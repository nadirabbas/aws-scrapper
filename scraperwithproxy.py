import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from amazoncaptcha import AmazonCaptcha
import re

def clean_url(url):
    return url.split("ref")[0].split("?")[0] if "ref" in url else url

def clean_img_url(url):
    if "._" in url:
        cleaned_url = url.split("._")[0] + "." + url.split(".")[-1]
        return cleaned_url.split("?")[0]
    else:
        return url

def extract_price(text):
    price_pattern = r'\$\d+\.\d{2}'
    matches = re.findall(price_pattern, text)
    return matches[0] if matches else None

def solve_captcha(driver):
    if driver.title.lower() == "Amazon.com".lower():
        print("Solving captcha...")
        count = 0
        solution = "Not solved"
        while solution.lower() == "Not solved".lower():
            if count > 0:
                print(f"Try {count} failed..")
                driver.refresh()
            captcha_url = driver.find_element(By.CSS_SELECTOR, "form img").get_attribute("src")
            captcha = AmazonCaptcha.fromlink(captcha_url)
            solution = captcha.solve()
            count += 1

        captcha_input = driver.find_element(By.ID, "captchacharacters")
        captcha_input.clear()
        captcha_input.send_keys(solution)
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

def click_element(driver, by, value, timeout=10):
    if get_element(driver, by, value):
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.element_to_be_clickable((by, value))).click()
            return True
        except:
            return False

def get_element_text(driver, by, value, default="-"):
    if get_element(driver, by, value):
        return get_element(driver,by, value).text
    else:
        return default

def get_element_attr(driver, by, value, attr, default="-"):
    if get_element(driver, by, value):
        return get_element(driver,by, value).get_attribute(attr)
    else:
        return default

def get_element(driver, by, value):
    if driver.find_elements(by, value):
        return driver.find_element(by, value)

def print_progress(current, total, start_time):
    elapsed_time = time.time() - start_time
    progress_percent = (current / total) * 100
    remaining_time = (elapsed_time / current) * (total - current)
    
    print(f"Processing: {current} ({progress_percent:.2f}%) | Elapsed: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time))} | Remaining: {time.strftime('%H:%M:%S', time.gmtime(remaining_time))}")

def read_txt(path):
    with open(path, "r") as file:
        return file.read()

def read_json(path):
    if len(read_txt(path)) > 0:
        with open(path, 'r', encoding="utf8") as out:
            return json.load(out)
    else:
        return []

def append_json(path, append):
    existing_data = read_json(path)
    existing_data.append(append)
    with open(path, 'w', encoding="utf8") as out:
        json.dump(existing_data, out, indent=4)

def extend_json(path, append):
    existing_data = read_json(path)
    existing_data.extend(append)
    with open(path, 'w', encoding="utf8") as out:
        json.dump(existing_data, out, indent=4)

def scrape_and_save(json_file, output_file):
    print("Script has started....")

    start_time = time.time()

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    with open(json_file, 'r', encoding="utf8") as f:
        data = json.load(f)

    total_items = len(data)


    for idx, item in enumerate(data):

        results = []
        print_progress(idx + 1, total_items, start_time)

        if item.get("title") in read_json("success.json"):
            continue

        url = item.get("url")
        driver.get(url)
        solve_captcha(driver)

        page_url = driver.current_url

        hardcover_swatch = get_element(driver, By.XPATH, "//*[contains(@class, 'swatchElement') and contains(., 'Hardcover')]")
        if hardcover_swatch:
            if "hardcover" in hardcover_swatch.text.lower():
                if "unselected" in hardcover_swatch.get_attribute("class").lower():
                    page_url = clean_url(get_element_attr(hardcover_swatch, By.TAG_NAME, "a", "href"))
                    driver.get(page_url)
                    solve_captcha(driver)
            else:
                append_json("success.json", item.get("title"))
                continue
        else:
            append_json("success.json", item.get("title"))
            continue

        title = item.get("title")
        category = item.get("category")
        tree = item.get("tree")
        category_url = item.get("category_url")
        reviews = get_element_text(driver, By.CSS_SELECTOR, ".reviewCountTextLinkedHistogram")
        ratings = get_element_text(driver, By.CSS_SELECTOR, "#acrCustomerReviewText", "0").replace("ratings", "").strip()
        price = extract_price(get_element_text(driver, By.XPATH, "//*[contains(@class, 'swatchElement') and contains(., 'Hardcover')]"))
        ships_from = get_element_text(driver, By.CSS_SELECTOR, ".tabular-buybox-text[tabular-attribute-name='Ships from']")
        sold_by = get_element_text(driver, By.CSS_SELECTOR, ".tabular-buybox-text[tabular-attribute-name='Sold by']")
        video_reviews = len(driver.find_elements(By.CSS_SELECTOR, "#vse-cards-vw-dp video"))

        # Description
        description = "-"
        description_div = get_element(driver, By.CSS_SELECTOR, "#bookDescription_feature_div")
        if description_div:
            description = description_div.text.replace("Read more", "").strip()
            if get_element(description_div, By.CSS_SELECTOR, ".a-expander-prompt"):
                if click_element(description_div, By.CSS_SELECTOR, ".a-expander-prompt"):
                    description = description_div.text.replace("Read less", "").strip()
        else:
            description = "-"

        # Editorial Review
        editorial_review = "-"
        editorial_reviews_div = get_element(driver, By.CSS_SELECTOR, "#editorialReviews_feature_div")
        if editorial_reviews_div:
            editorial_review = editorial_reviews_div.text.replace("Read more", "").strip()
            if get_element(editorial_reviews_div, By.CSS_SELECTOR, ".a-expander-prompt"):
                if click_element(editorial_reviews_div, By.CSS_SELECTOR, ".a-expander-prompt"):
                    editorial_review = editorial_reviews_div.text.replace("Read less", "").strip()
        else:
            editorial_review = "-"

        # Pictures
        img_urls = []
        image_thumbs = driver.find_elements(By.CSS_SELECTOR, ".imageThumb")
        img_urls = [clean_img_url(img_thumb.find_element(By.TAG_NAME, "img").get_attribute("src")) for img_thumb in image_thumbs]

        # Product details
        a_list_items = driver.find_elements(By.CSS_SELECTOR, "#detailBullets_feature_div .a-list-item")
        product_details = {}
        if len(a_list_items) > 0:
            for list_item in a_list_items:
                spans = list_item.find_elements(By.TAG_NAME, "span")
                if len(spans) >= 2:
                    if "Customer Reviews".lower() not in spans[0].text.lower():
                        key = spans[0].text.strip(":").strip()
                        value = spans[1].text.strip()
                        if "Best Sellers Rank".lower() in key.lower():
                            value = list_item.text.split(":")[1].strip().split(" ")[0].replace("#", "").strip()
                        product_details[key] = value
        else:
            carousel_cards = driver.find_elements(By.CSS_SELECTOR, "li.rpi-carousel-attribute-card div")
            for list_item in carousel_cards:
                divs = list_item.find_elements(By.CSS_SELECTOR, "div")
                if len(divs) >= 3:
                    key = divs[0].get_attribute("textContent").strip()
                    value = divs[2].get_attribute("textContent").strip()
                    if key not in product_details:  # Check if the key already exists in the dictionary
                        product_details[key] = value

        results.append({
            "title": title,
            "price": price,
            "description": description,
            "product_details": product_details,
            "images": img_urls,
            "reviews": reviews,
            "ratings": ratings,
            "video_reviews": video_reviews,
            "ships_from": ships_from,
            "sold_by": sold_by,
            "editorial_review": editorial_review,
            "url": page_url,
            "category": category,
            "category_url": category_url,
            "tree": tree
        })

        extend_json(output_file, results)
        append_json("success.json", item.get("title"))
        

    driver.quit()

# Usage
scrape_and_save("input.json", "output.json")
