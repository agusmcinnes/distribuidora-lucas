import os
import requests
import msal

# Power BI API credentials (from environment variables)
TENANT_ID = os.environ.get("POWERBI_TENANT_ID", "")
CLIENT_ID = os.environ.get("POWERBI_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("POWERBI_CLIENT_SECRET", "")
DATASET_ID = os.environ.get("POWERBI_DATASET_ID", "")
GROUP_ID = os.environ.get("POWERBI_GROUP_ID", "")

# Azure AD and Power BI endpoints
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]
POWERBI_API_URL = "https://api.powerbi.com/v1.0/myorg"


def get_access_token():
    """Acquire access token using client credentials flow."""
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        print("Successfully acquired access token")
        return result["access_token"]
    else:
        error = result.get("error", "Unknown error")
        error_description = result.get("error_description", "No description")
        raise Exception(f"Failed to acquire token: {error} - {error_description}")


def test_dataset_connection(access_token):
    """Test connection by retrieving dataset information."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "queries": [
            {
                "query": "EVALUATE TOPN(100, 'VENTAS')"
            }
        ],
    }

    # Get datasets from workspace (required for service principal)
    # Using group-scoped endpoint instead of /myorg/
    url = f"{POWERBI_API_URL}/groups/{GROUP_ID}/datasets/{DATASET_ID}/executeQueries"
    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 200:
        dataset_info = response.json()
        print("\nConnection successful!")
        print(f"DATASET INFO: {dataset_info}")
        print(f"Dataset Name: {dataset_info.get('name', 'N/A')}")
        print(f"Dataset ID: {dataset_info.get('id', 'N/A')}")
        print(f"Configured By: {dataset_info.get('configuredBy', 'N/A')}")
        print(f"Is Refreshable: {dataset_info.get('isRefreshable', 'N/A')}")
        print(f"Is Effective Identity Required: {dataset_info.get('isEffectiveIdentityRequired', 'N/A')}")
        return dataset_info
    else:
        print(f"\nConnection failed!")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def main():
    print("Testing Power BI Dataset Connection")
    print("=" * 40)

    try:
        # Step 1: Get access token
        print("\nStep 1: Acquiring access token...")
        token = get_access_token()

        # Step 2: Test dataset connection
        print("\nStep 2: Testing dataset connection...")
        test_dataset_connection(token)

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
