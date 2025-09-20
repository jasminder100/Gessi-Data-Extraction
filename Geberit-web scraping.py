from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time
import pandas as pd
import os

# 📁 Setup Paths
download_path = r"C:\Users\jasminder\Downloads\whisky"
excel_path = os.path.join(download_path, "geberit_products_5533344.xlsx")
csv_path = os.path.join(download_path, "geberit_products_data_5533344.csv")

# 🔧 Chrome Options
chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_path,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True,
}
chrome_options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

main_url = "https://catalog.geberit-global.com/en-GU"
driver.get(main_url)
time.sleep(5)

columns = ["Category", "Sub-Category", "Product", "Sub-Product", "Image URL", "Download Link", "Article Number"]
data = []

def save_progress():
    df = pd.DataFrame(data, columns=columns)
    df["Download Link"] = df["Sub-Product"].apply(lambda name: f"{name}.pdf")
    df.to_excel(excel_path, index=False)
    df.to_csv(csv_path, index=False)
    print(f"✅ Progress saved. Rows: {len(data)}")
    df["Download Link"] = df["Sub-Product"].apply(lambda name: f"{name}.pdf")

def get_all_sub_product_elements():
    last_count = 0
    retries = 0
    max_retries = 5

    while True:
        elements = driver.find_elements(By.XPATH, "//p[@class='chakra-text css-1mayizw']")
        current_count = len(elements)

        if current_count == last_count:
            retries += 1
            if retries >= max_retries:
                break
        else:
            retries = 0
            last_count = current_count

        if elements:
            ActionChains(driver).move_to_element(elements[-1]).perform()
        time.sleep(2)

    return elements

# Step 1: Get all categories
wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.chakra-link.css-spn4bz')))
soup = BeautifulSoup(driver.page_source, "html.parser")
category_elements = soup.find_all("a", class_="chakra-link css-spn4bz")

categories = []
for cat in category_elements:
    name = cat.get_text(strip=True)
    href = cat.get("href")
    if name and href:
        url = href if href.startswith("http") else "https://catalog.geberit-global.com" + href
        categories.append((name, url))

for cat_name, cat_url in categories:
    driver.get(cat_url)
    time.sleep(5)

    # Get sub-category names
    sub_soup = BeautifulSoup(driver.page_source, "html.parser")
    sub_elements = sub_soup.select("div.css-1lidi8t p.chakra-text.css-3jydma")
    sub_category_names = [el.get_text(strip=True) for el in sub_elements]

    for sub_name in sub_category_names:
        try:
            sub_elem = wait.until(EC.element_to_be_clickable((By.XPATH, f"//p[text()='{sub_name}']")))
            sub_elem.click()
            time.sleep(5)
            subcat_url = driver.current_url

            # Get product names
            prod_soup = BeautifulSoup(driver.page_source, "html.parser")
            prod_elements = prod_soup.select("div.css-1lidi8t p.chakra-text.css-3jydma")
            prod_names = [el.get_text(strip=True) for el in prod_elements]

            for prod_name in prod_names:
                try:
                    prod_elem = wait.until(EC.element_to_be_clickable((By.XPATH, f"//p[text()='{prod_name}']")))
                    prod_elem.click()
                    time.sleep(5)
                    prod_url = driver.current_url

                    # Extract sub-product names
                    name_elements = get_all_sub_product_elements()
                    sub_product_names = [el.text.strip() for el in name_elements if el.text.strip()]

                    print(f"\n🔍 Found {len(sub_product_names)} sub-products under product: {prod_name}")
                    print("🧾 Sub-Product Names:")
                    for i, name in enumerate(sub_product_names, 1):
                        print(f"{i}. {name}")

                    # Now for each sub-product name, find its clickable link properly
                    for sub_prod_name in sub_product_names:
                        try:
                            # Locate the clickable link by searching for <a> that contains a child <p> with sub-product name
                            sub_prod_link_elem = wait.until(EC.element_to_be_clickable((
                                By.XPATH,
                                f"//a[contains(@class, 'chakra-linkbox__overlay')]//p[text()='{sub_prod_name}']/ancestor::a"
                            )))

                            # Get image URL associated with this sub-product
                            img_elem = None
                            try:
                                # Find img sibling within the same container of this link
                                img_elem = sub_prod_link_elem.find_element(By.XPATH, ".//img")
                            except:
                                pass

                            image_url = img_elem.get_attribute("src") if img_elem else None
                            if image_url:
                                image_url = image_url.replace("__", "_", 1)

                            # Click the sub-product link
                            sub_prod_link_elem.click()
                            time.sleep(5)

                            try:
                                opened_name_elem = driver.find_element(By.XPATH, "//h1[@class='chakra-heading css-12mjs1n']/span")
                                opened_name = opened_name_elem.text.strip()
                            except:
                                opened_name = sub_prod_name

                            # 📁 Prepare download path
                            #download_folder = os.path.join(download_path, "downloads55333444", cat_name, sub_name, prod_name, opened_name)
                            download_folder = os.path.join(download_path, "downloads55333444", prod_name, opened_name)

                            os.makedirs(download_folder, exist_ok=True)
                            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                                "behavior": "allow",
                                "downloadPath": download_folder
                            })

                            try:
                                download_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'pdp-download-pdf')]")))
                                download_button.click()
                                time.sleep(3)
                            except:
                                pass

                            try:
                                pdf_link_elem = driver.find_element(By.XPATH, "//a[contains(@href, '.pdf')]")
                                pdf_url = pdf_link_elem.get_attribute("href")
                            except:
                                pdf_url = driver.current_url

                            try:
                                article_elem = wait.until(EC.presence_of_element_located((
                                    By.XPATH,
                                    "//div[contains(@class, 'sc-c70d150d-2')]//span[contains(@class, 'sc-1f8c92fc-0')]"
                                )))
                                article_number = article_elem.text
                            except:
                                article_number = "[Not Found]"

                            data.append([cat_name, sub_name, prod_name, opened_name, image_url, pdf_url, article_number])
                            save_progress()

                            driver.get(prod_url)
                            time.sleep(4)

                        except Exception as e:
                            print(f"⚠️ Sub-product click failed for '{sub_prod_name}': {e}")
                            driver.get(prod_url)
                            time.sleep(4)

                    driver.get(subcat_url)
                    time.sleep(4)

                except Exception as prod_err:
                    print(f"⚠️ Product click failed: {prod_err}")
                    driver.get(subcat_url)
                    time.sleep(4)

            driver.get(cat_url)
            time.sleep(4)
        except Exception as sub_err:
            print(f"⚠️ Sub-category click failed: {sub_err}")
            driver.get(cat_url)
            time.sleep(4)
    driver.get(main_url)
    time.sleep(5)
# ✅ Final Save
save_progress()
driver.quit()
print("✅ Script Completed. Browser Closed.")
