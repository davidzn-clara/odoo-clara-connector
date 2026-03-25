import base64
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta

import requests
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class RetryableError(Exception):
    """Exception raised for transient Clara API errors like 429 or 5xx that can be retried."""
    pass


class ClaraAPIService:
    def __init__(self, env):
        self.env = env
        
        # We fetch company explicitly using env.company to get global settings
        company = self.env.company
        
        self.country = company.clara_country or 'mx'
        self.client_id = company.clara_client_id
        self.client_secret = company.clara_client_secret
        self.tax_identifier = company.clara_tax_identifier
        
        config = self.env['ir.config_parameter'].sudo()
        self.timeout = int(config.get_param('clara_connector.clara_request_timeout', 30))
        self.base_url = f"https://public-api.{self.country}.clara.com"

        self.ca_cert = company.clara_ca_cert
        self.client_cert = company.clara_client_cert
        self.client_key = company.clara_client_key

    def _create_temp_cert_files(self):
        """Write base64 certs to temporary files and return their paths. Caller must delete them!"""
        if not self.ca_cert or not self.client_cert or not self.client_key:
            raise UserError(_("Missing Clara mTLS certificates. Please upload them in Configuration."))

        ca_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        ca_file.write(base64.b64decode(self.ca_cert))
        ca_file.close()

        cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        cert_file.write(base64.b64decode(self.client_cert))
        cert_file.close()

        key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        key_file.write(base64.b64decode(self.client_key))
        key_file.close()

        return ca_file.name, cert_file.name, key_file.name

    def _cleanup_temp_files(self, *file_paths):
        for path in file_paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as e:
                    _logger.warning("Failed to delete temp cert file %s: %s", path, e)

    def _handle_response_error(self, response):
        status = response.status_code
        if status < 400:
            return
            
        try:
            body = response.json()
        except ValueError:
            body = response.text
            
        _logger.debug("Clara API Error %s: %s", status, body)

        if status == 401:
            raise UserError(_("Clara authentication failed. Check your Client ID, Secret, and certificates."))
        elif status == 403:
            raise UserError(_("Clara authorization error. Verify the API user has Company Owner role."))
        elif status == 429:
            raise RetryableError(_("Clara rate limit reached. The sync will retry automatically."))
        elif status >= 500:
            raise RetryableError(_("Clara service is temporarily unavailable. Try again later."))
        else:
            _logger.error("Clara API Error %s: %s", status, body)
            raise UserError(_("Clara API returned error code %s: %s") % (status, body))

    def get_token(self):
        config = self.env['ir.config_parameter'].sudo()
        token = config.get_param('clara_connector.access_token')
        expiry_str = config.get_param('clara_connector.access_token_expiry')

        if token and expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() < (expiry - timedelta(seconds=60)):
                return token

        if not self.client_id or not self.client_secret:
            raise UserError(_("Clara Client ID and Secret are missing in configuration."))

        ca_path = cert_path = key_path = None
        try:
            ca_path, cert_path, key_path = self._create_temp_cert_files()

            url = f"{self.base_url}/oauth/token"
            data = {
                "grant_type": "client_credentials",
            }

            # Clara requires credentials as Basic Auth header
            raw = f"{self.client_id}:{self.client_secret}"
            encoded = base64.b64encode(raw.encode('utf-8')).decode('utf-8')
            headers = {
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            try:
                response = requests.post(
                    url,
                    data=data,
                    headers=headers,
                    cert=(cert_path, key_path),
                    verify=True,
                    timeout=self.timeout
                )
            except requests.exceptions.RequestException as e:
                _logger.error("Clara API Network Error: %s", e)
                raise RetryableError(_("Network error connecting to Clara API: %s") % str(e))

            self._handle_response_error(response)

            resp_json = response.json()
            new_token = resp_json.get('access_token')
            expires_in = resp_json.get('expires_in', 3600)

            # Save token
            config.set_param('clara_connector.access_token', new_token)
            config.set_param('clara_connector.access_token_expiry', (datetime.now() + timedelta(seconds=expires_in)).isoformat())

            return new_token
        except Exception as e:
            _logger.error("Error fetching Clara Token: %s", str(e))
            raise
        finally:
            self._cleanup_temp_files(ca_path, cert_path, key_path)

    def _make_request(self, method, endpoint, params=None, json_data=None):
        if not self.tax_identifier:
            raise UserError(_("Company Tax Identifier (RFC/NIT/CNPJ) is required for Clara synchronizations."))

        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tax-Identifier": self.tax_identifier,
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}{endpoint}"
        ca_path = cert_path = key_path = None

        try:
            ca_path, cert_path, key_path = self._create_temp_cert_files()

            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    cert=(cert_path, key_path),
                    verify=True,
                    timeout=self.timeout
                )
            except requests.exceptions.RequestException as e:
                _logger.error("Clara API Network Error: %s", e)
                raise RetryableError(_("Network error connecting to Clara API: %s") % str(e))

            self._handle_response_error(response)
            
            try:
                resp_json = response.json()
                _logger.info("Clara API Response [%s %s]: %s", method, endpoint, str(resp_json)[:500])
                
                # Debug: Write last response to file for inspection
                try:
                    import os
                    # Get the directory where THIS file is located (clara_api_service.py is in services/)
                    service_dir = os.path.dirname(os.path.abspath(__file__))
                    # Go up one level to the module root (clara_connector/)
                    module_root = os.path.dirname(service_dir)
                    debug_file = os.path.join(module_root, 'clara_last_response.json')
                    
                    with open(debug_file, 'w') as f:
                        json.dump({
                            'endpoint': endpoint,
                            'method': method,
                            'timestamp': datetime.now().isoformat(),
                            'payload': resp_json
                        }, f, indent=2)
                except Exception as ef:
                    _logger.warning("Failed to write debug file: %s", ef)
                    
                return resp_json
            except ValueError:
                _logger.info("Clara API Response [%s %s]: %s", method, endpoint, response.text[:500])
                return {}

        except Exception as e:
            _logger.error("Error calling Clara API %s: %s", endpoint, str(e))
            raise
        finally:
            self._cleanup_temp_files(ca_path, cert_path, key_path)

    def _paginate(self, endpoint, params, data_key=None, max_records=5000):
        results = []
        page = params.get('page', 0)
        while True:
            params['page'] = page
            data = self._make_request('GET', endpoint, params=params)

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Check for specific key, then typical pagination/wrapper keys
                items = []
                for key in [data_key, 'content', 'data', 'items']:
                    if key and key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                
                # If no key matched, fallback to finding the first list value in the dict
                if not items:
                    for val in data.values():
                        if isinstance(val, list):
                            items = val
                            break
            else:
                items = []

            if not items:
                break

            results.extend(items)

            if len(results) >= max_records:
                _logger.warning("Clara Sync reached max_records limit (%s) for %s", max_records, endpoint)
                break

            # Typical cursor validation using pagination metadata
            meta = data.get('meta', {}) if isinstance(data, dict) else {}
            raw_total = meta.get('totalPages') or meta.get('total_pages')
            if raw_total is not None:
                try:
                    total_pages: int = int(str(raw_total))
                    if page >= total_pages:
                        break
                except (ValueError, TypeError):
                    pass

            page = page + 1

        return list(results)

    # ----------------------------------------------------
    # Endpoint Methods
    # ----------------------------------------------------

    def get_transactions(self, from_date=None, to_date=None, status=None, page=0, limit=100, max_records=5000):
        params = {"size": limit, "page": page}
        if from_date:
            params["operationDateRangeStart"] = from_date.strftime("%Y-%m-%d")
        if to_date:
            params["operationDateRangeEnd"] = to_date.strftime("%Y-%m-%d")
        if status:
            params["status"] = status
            
        return self._paginate("/api/v3/transactions", params, data_key="transactions", max_records=max_records)

    def get_transaction(self, uuid):
        return self._make_request('GET', f"/api/v3/transactions/{uuid}")

    def get_cards(self, status=None, page=0, limit=100, max_records=5000):
        params = {"size": limit, "page": page}
        if status:
            params["status"] = status
        # API v3 uses 'content' for list mapping
        return self._paginate("/api/v3/cards", params, data_key="content", max_records=max_records)

    def get_card(self, uuid):
        return self._make_request('GET', f"/api/v3/cards/{uuid}")

    def get_billing_statements(self, page=0, limit=100, max_records=5000):
        params = {"size": limit, "page": page}
        return self._paginate("/api/v3/billing-statements", params, data_key="statements", max_records=max_records)

    def get_billing_statement(self, uuid):
        return self._make_request('GET', f"/api/v3/billing-statements/{uuid}")

    def get_statement_transactions(self, statement_uuid, page=0, limit=100, max_records=5000):
        params = {"size": limit, "page": page}
        return self._paginate(f"/api/v3/billing-statements/{statement_uuid}/transactions", params, data_key="transactions", max_records=max_records)

    def get_users(self, page=0, limit=100, max_records=5000):
        params = {"size": limit, "page": page}
        return self._paginate("/api/v3/users", params, data_key="users", max_records=max_records)
