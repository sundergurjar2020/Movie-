import requests
import os
from collections import deque

# --- Constants ---
AUTHORITY = "api.classplusapp.com"
PATH_1 = "/v2/courses?tabCategoryId=1"
URL_1 = f"https://{AUTHORITY}{PATH_1}"
BASE_PATH_2 = "/v2/course/content/get?courseId={course_id}&folderId={folder_id}&storeContentEvent=false" 

OUTPUT_FILE = "extracted_content_links.txt"

# --- Functions ---
def get_headers_with_token(token: str, device_id: str) -> dict:
    return {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate", 
        "accept-language": "en",
        "api-version": "52",
        "device-id": device_id,
        "origin": "https://web.classplusapp.com",
        "priority": "u=1, i",
        "referer": "https://web.classplusapp.com/",
        "region": "IN",
        "sec-ch-ua": '"Chromium";v="142", "Brave";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0",
        "x-access-token": token, 
    }

def select_course_details(token: str) -> tuple[int, str, float] | None:
    headers = get_headers_with_token(token, device_id="841")
    try:
        response = requests.get(URL_1, headers=headers, timeout=10)
        response.raise_for_status()
        courses_list = response.json().get('data', {}).get('courses', [])
        if not courses_list:
            print("❌ No courses found.")
            return None

        print("\n📚 Available Courses:")
        course_map = {}
        for index, course in enumerate(courses_list):
            selection_number = str(index + 1)
            course_map[selection_number] = {
                "id": course.get('id'),
                "name": course.get('name', 'N/A'),
                "totalAmount": course.get('totalAmount')
            }
            price_tag = f"₹{course.get('totalAmount')}" if course.get('totalAmount') != 0 else "FREE"
            print(f"[{selection_number}]. {course.get('name')} ({price_tag})")

        while True:
            selection = input("Enter course number to extract: ")
            if selection in course_map:
                selected = course_map[selection]
                return selected['id'], selected['name'], selected['totalAmount']
            else:
                print("❌ Invalid selection. Try again.")

    except Exception as e:
        print(f"❌ Error fetching courses: {e}")
        return None

def scrape_folder_content(token: str, course_id: int, folder_id: int, folder_name: str, folder_queue: deque, output_file: str):
    url_2 = f"https://{AUTHORITY}{BASE_PATH_2.format(course_id=course_id, folder_id=folder_id)}"
    headers = get_headers_with_token(token, device_id="713")
    try:
        response = requests.get(url_2, headers=headers, timeout=10)
        if response.status_code == 304:
            return
        response.raise_for_status()
        content_list = response.json().get('data', {}).get('courseContent', [])
        if not content_list:
            return

        with open(output_file, 'a', encoding='utf-8') as f:
            for item in content_list:
                # Folder
                if 'id' in item and 'name' in item and item.get('contentType') == 1:
                    folder_queue.append({"id": item['id'], "name": item['name'], "parent_name": folder_name})
                # Video -> https://cpmc/contentHashId
                elif 'uuid' in item and 'contentHashId' in item:
                    f.write(f"[{folder_name}] {item.get('name')} : https://cpmc/{item.get('contentHashId')}\n")
                # PDF/Doc -> original URL
                elif 'url' in item and item.get('format') in ['pdf', 'document']:
                    f.write(f"[{folder_name}] {item.get('name')} : {item.get('url')}\n")

    except Exception as e:
        print(f"❌ Error in folder '{folder_name}': {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Ask for API token
    API_ACCESS_TOKEN = input("Enter your API Access Token: ").strip()
    if not API_ACCESS_TOKEN:
        print("🛑 Token not provided. Exiting.")
        exit()

    course_info = select_course_details(API_ACCESS_TOKEN)
    if course_info is None:
        print("🛑 Aborting process.")
        exit()

    extracted_course_id, course_name, total_amount = course_info
    safe_course_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '_')).rstrip()
    OUTPUT_FILE = f"{safe_course_name}.txt"

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    # Fetch root content
    url_root = f"https://{AUTHORITY}{BASE_PATH_2.format(course_id=extracted_course_id, folder_id=0)}"
    headers_root = get_headers_with_token(API_ACCESS_TOKEN, device_id="713")
    try:
        root_content = requests.get(url_root, headers=headers_root, timeout=10).json().get('data', {}).get('courseContent', [])
    except Exception as e:
        print(f"❌ Failed fetching root content: {e}")
        exit()

    folder_queue = deque()
    for item in root_content:
        if 'id' in item and 'name' in item and item.get('contentType') == 1:
            folder_queue.append({"id": item['id'], "name": item['name'], "parent_name": "Root"})

    while folder_queue:
        current_folder = folder_queue.popleft()
        scrape_folder_content(API_ACCESS_TOKEN, extracted_course_id, current_folder['id'], current_folder['name'], folder_queue, OUTPUT_FILE)

    print(f"\n🎉 Scraping complete! All links saved in: {OUTPUT_FILE}")

    # Colab specific: download option
    try:
        from google.colab import files
        files.download(OUTPUT_FILE)
    except:
        pass
