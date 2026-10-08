import requests
import base64
import time


# ============================================================
# CONFIG
# ============================================================

JUDGE0_URL = "http://localhost:2358"


# ============================================================
# BASE64 FUNCTIONS
# ============================================================

def encode_base64(text: str) -> str:
    """
    String -> Base64
    """
    return base64.b64encode(
        text.encode("utf-8")
    ).decode("utf-8")


def decode_base64(text: str | None) -> str | None:
    """
    Base64 -> String
    """
    if text is None:
        return None

    return base64.b64decode(
        text
    ).decode("utf-8", errors="replace")


# ============================================================
# SOURCE CODE
# ============================================================

source_code = r'''
#include <iostream>
using namespace std;

int main() {

    int a, b;

    while (cin >> a >> b) {
        cout << a + b << endl;
    }

    return 0;
}
'''


# ============================================================
# INPUT
# ============================================================

stdin = """10 20
1 2
100 200
"""


# ============================================================
# ENCODE SOURCE CODE + INPUT
# ============================================================

source_code_b64 = encode_base64(source_code)
stdin_b64 = encode_base64(stdin)


print("===== ORIGINAL SOURCE CODE =====")
print(source_code)

print("===== SOURCE CODE BASE64 =====")
print(source_code_b64)

print("===== ORIGINAL INPUT =====")
print(stdin)

print("===== INPUT BASE64 =====")
print(stdin_b64)


# ============================================================
# SUBMIT TO JUDGE0
# ============================================================

payload = {
    "language_id": 54,          # GNU++17

    # Source code đã Base64
    "source_code": source_code_b64,

    # stdin đã Base64
    "stdin": stdin_b64
}


response = requests.post(
    f"{JUDGE0_URL}/submissions",
    params={
        "base64_encoded": "true",
        "wait": "false"
    },
    json=payload
)


# ============================================================
# CHECK SUBMISSION RESPONSE
# ============================================================

print("\n===== SUBMISSION HTTP RESPONSE =====")

print("HTTP status:", response.status_code)

submission_response = response.json()

print("Raw response:")
print(submission_response)


# Lấy token
token = submission_response["token"]

print("\nToken:")
print(token)


# ============================================================
# WAIT FOR RESULT
# ============================================================

print("\n===== WAITING FOR JUDGE0 =====")

while True:

    response = requests.get(
        f"{JUDGE0_URL}/submissions/{token}",
        params={
            "base64_encoded": "true"
        }
    )

    result = response.json()

    status_id = result["status"]["id"]
    status_description = result["status"]["description"]

    print(
        f"Status: {status_id} - {status_description}"
    )

    # 1 = In Queue
    # 2 = Processing
    # >= 3 = đã hoàn thành
    if status_id >= 3:
        break

    time.sleep(1)


# ============================================================
# DECODE RESULT
# ============================================================

print("\n========================================")
print("           JUDGE0 RESULT")
print("========================================")


# -----------------------------
# Status
# -----------------------------

print("\nStatus:")
print(result["status"])


# -----------------------------
# stdout
# -----------------------------

stdout_b64 = result.get("stdout")

print("\nstdout BASE64:")
print(stdout_b64)

stdout = decode_base64(stdout_b64)

print("\nstdout DECODED:")
print(stdout)


# -----------------------------
# stderr
# -----------------------------

stderr_b64 = result.get("stderr")

print("\nstderr BASE64:")
print(stderr_b64)

stderr = decode_base64(stderr_b64)

print("\nstderr DECODED:")
print(stderr)


# -----------------------------
# compile_output
# -----------------------------

compile_output_b64 = result.get("compile_output")

print("\ncompile_output BASE64:")
print(compile_output_b64)

compile_output = decode_base64(compile_output_b64)

print("\ncompile_output DECODED:")
print(compile_output)


# -----------------------------
# message
# -----------------------------

message_b64 = result.get("message")

print("\nmessage BASE64:")
print(message_b64)

message = decode_base64(message_b64)

print("\nmessage DECODED:")
print(message)


# -----------------------------
# time
# -----------------------------

print("\ntime:")
print(result.get("time"))


# -----------------------------
# memory
# -----------------------------

print("\nmemory:")
print(result.get("memory"))


# -----------------------------
# token
# -----------------------------

print("\ntoken:")
print(result.get("token"))


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n========================================")
print("             FINAL SUMMARY")
print("========================================")

print("Verdict :", result["status"]["description"])
print("Output  :", repr(stdout))
print("Error   :", repr(stderr))
print("Compile :", repr(compile_output))
print("Message :", repr(message))
print("Time    :", result.get("time"))
print("Memory  :", result.get("memory"))