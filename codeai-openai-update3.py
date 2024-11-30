import os
import json
import traceback
import requests
# from html2text import HTML2Text  #!~

# Configuration for single-city scraping
singular_city = True  # Set to False to scrape all cities
singular_city_id = 'abilene'  # Single city name (case-insensitive)

# API Endpoints
cities_url = "https://api.municode.com/Clients/stateAbbr?stateAbbr=tx"
client_content_url = lambda city_id: f"https://api.municode.com/ClientContent/{city_id}"
codes_toc_url = lambda product_id, job_id: f"https://api.municode.com/codesToc?productId={product_id}&jobId={job_id}"
job_id_url = lambda product_id: f"https://api.municode.com/Jobs/latest/{product_id}"
# codes_content_url = lambda node_id, product_id: f"https://api.municode.com/CodesContent?nodeId={node_id}&productId={product_id}&showChanges=true"  #!~


# Fetch all cities in Texas
def get_cities():
    response = requests.get(cities_url)
    response.raise_for_status()
    data = response.json()
    return [{
        "ClientID": city["ClientID"],
        "ClientName": city["ClientName"],
        "StateName": city["State"]["StateName"]
    } for city in data]

# Fetch content codes for a specific city
def get_client_content(city_id):
    response = requests.get(client_content_url(city_id))
    response.raise_for_status()
    data = response.json()
    return [(code["productId"], code["productName"]) for code in data["codes"]]

# Fetch latest job ID for a product
def get_job_id(product_id):
    response = requests.get(job_id_url(product_id))
    response.raise_for_status()
    data = response.json()
    return data["Id"]

# ===== ===== =====
def get_children(product_id, job_id):
    response = requests.get(codes_toc_url(product_id, job_id))
    response.raise_for_status()
    data = response.json()
    return data["Children"]

def normalize_text_simple(text):
    if not isinstance(text, str):
        return text
    return "\n".join([line.strip() for line in text.split("\n") if line.strip()])

def get_docs(product_id, job_id, node_id):
    url = f"https://api.municode.com/CodesContent?jobId={job_id}&nodeId={node_id}&productId={product_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return (
        [
            {
                "Id": doc["Id"],
                "Title": doc["Title"],
                "Content": normalize_text_simple(doc["Content"]),
                "DocOrderId": doc["DocOrderId"],
            }
            for doc in data["Docs"]
        ],
        data["ShowToc"]
    )

def get_tocs(product_id, job_id, node_id):
    url = f"https://api.municode.com/codesToc/children?jobId={job_id}&nodeId={node_id}&productId={product_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return [
        {
            "Id": child["Id"],
            "Heading": child["Heading"],
            "HasChildren": child["HasChildren"],
        }
        for child in data
    ]

def get_data_of_leaf(product_id, job_id, node_id):
    url = f"https://api.municode.com/CodesContent?jobId={job_id}&nodeId={node_id}&productId={product_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    doc = data["Docs"][0]
    DocType = doc["DocType"]
    Id = doc["Id"]
    Title = doc["Title"]
    Content = doc["Content"]
    if DocType == 1:
        return {"Title": Title, "Content": Content}
    elif DocType == 2:
        pdf_url = f"https://mcclibrary.blob.core.usgovcloudapi.net/codecontent/{product_id}/{job_id}/{Id}.pdf"
        return {"Title": Title, "ContentPdfUrl": pdf_url}
    else:
        print(f"We need to analyze this case : DocType = {DocType}")
        return None

def get_child_data(docs, product_id, job_id, node_id):
    url = f"https://api.municode.com/codesToc/children?jobId={job_id}&nodeId={node_id}&productId={product_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    result_data = []
    for data_level in data:
        id = data_level["Id"]
        heading = data_level["Heading"]
        hasChildren = data_level["HasChildren"]
        docOrderId = data_level["DocOrderId"]
        print(f"Getting data of -- {heading}")
        if not hasChildren:
            result_data.append({"heading": heading, "data": docs[docOrderId]})
        else:
            result_data.append({"heading": heading, "content": docs[docOrderId]["Content"], "data": get_child_data(docs, product_id, job_id, id)})
        print((f"Getting data of -- {heading} -- Done!"))
    return result_data

def get_content_from_tocs(product_id, job_id, tocs_data):
    result_data = []
    for index, toc_data in enumerate(tocs_data):
        # if index > 4: break
        Id, Heading, HasChildren = toc_data["Id"], toc_data["Heading"], toc_data["HasChildren"]
        print(f"Getting data of -- {Heading}")
        if not HasChildren:
            content_data = get_data_of_leaf(product_id, job_id, Id)
            result_data.append({"heading": Heading, "data": content_data})
        else:
            docs, show_toc = get_docs(product_id, job_id, Id)
            if not show_toc:
                docs_dict = {
                    doc["DocOrderId"]: {
                        "Title": doc["Title"],
                        "Content": doc["Content"],
                    }
                    for doc in docs
                }
                content_data = get_child_data(docs_dict, product_id, job_id, Id)
                result_data.append({"heading": Heading, "data": content_data})
            else:
                tocs = get_tocs(product_id, job_id, Id)
                content_data = get_content_from_tocs(product_id, job_id, tocs)
                result_data.append({"heading": Heading, "data": content_data})
        print((f"Getting data of -- {Heading} -- Done!"))
    return result_data

# #!~ Convert HTML content to Markdown
# def convert_html_to_md(html_content):
#     converter = HTML2Text()
#     converter.ignore_links = True
#     converter.ignore_images = True
#     return converter.handle(html_content)

# Scrape cities and save results
def scrape_cities():
    try:
        all_cities = get_cities()

        # Filter for a single city if required
        if singular_city:
            my_cities = [
                city for city in all_cities if city["ClientName"].lower() == singular_city_id.lower()
            ]
            if not my_cities:
                print(f"City '{singular_city_id}' not found in the API response.")
                return
        else:
            my_cities = all_cities

        failed_cities = []

        for city in my_cities:
            print(f"Processing city: {city['ClientName']}")
            try:
                result_all = []
                product_ids = get_client_content(city["ClientID"])
                for product_id, product_name in product_ids:
                    print(f"  Working on product_name: {product_name}")
                    job_id = get_job_id(product_id)
                    tocs_data = get_children(product_id, job_id)
                    result_data = get_content_from_tocs(product_id, job_id, tocs_data)
                    result_all.append({
                        "product_name": product_name,
                        "product_data": result_data
                    })

                # Save output
                output_dir = "./output"
                os.makedirs(output_dir, exist_ok=True)
                with open(os.path.join(output_dir, f"{city['ClientName']}-{city['StateName']}.json"), "w") as f:
                    json.dump(result_all, f, indent=4)

            except Exception as e:
                print(f"Failed to scrape codes for city: {city['ClientName']}")
                detail = f"Error: {str(e)}\n{traceback.format_exc()}"
                print(detail)
                failed_cities.append(city["ClientName"])

        print("Failed cities:")
        print(failed_cities)

    except Exception as e:
        print(f"Error fetching cities: {e}")

if __name__ == "__main__":
    scrape_cities()
