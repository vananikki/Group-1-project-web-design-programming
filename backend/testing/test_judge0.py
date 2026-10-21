
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException


# =========================================================
# CONFIGURATION
# =========================================================

JUDGE0_URL = "http://localhost:2358"
TIMEOUT = 5


# =========================================================
# PING JUDGE0
# =========================================================

def ping_judge0() -> bool:
    """
    Kiểm tra Judge0 local có phản hồi hay không.
    Trả về True nếu endpoint /languages phản hồi HTTP 200.
    """

    url = f"{JUDGE0_URL}/languages"

    print(f"Checking Judge0 at: {JUDGE0_URL}")

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            print("[OK] Judge0 is reachable.")
            print(f"[OK] HTTP status: {response.status_code}")
            return True

        print(f"[ERROR] HTTP status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False

    except ConnectionError:
        print("[ERROR] Cannot connect to Judge0.")
        print("Check that the Judge0 Docker containers are running.")
        return False

    except Timeout:
        print("[ERROR] Request timed out.")
        return False

    except RequestException as error:
        print(f"[ERROR] Request failed: {error}")
        return False


# =========================================================
# GET AVAILABLE LANGUAGES
# =========================================================

def get_languages() -> None:
    """Lấy danh sách ngôn ngữ compiler mà Judge0 cung cấp."""

    url = f"{JUDGE0_URL}/languages"

    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        languages = response.json()

        print(f"\nAvailable languages: {len(languages)}")
        print("-" * 55)

        for language in languages:
            print(
                f"ID: {language['id']:>4} | "
                f"Name: {language['name']}"
            )

    except RequestException as error:
        print(f"[ERROR] Cannot retrieve languages: {error}")

    except (ValueError, KeyError, TypeError) as error:
        print(f"[ERROR] Invalid response from Judge0: {error}")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    if ping_judge0():
        get_languages()
