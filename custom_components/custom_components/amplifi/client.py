import re
import logging
import json

_LOGGER = logging.getLogger(__name__)


class AmplifiClientError(Exception):
    """Generic error of Amplifi client."""

    pass


class AmplifiClient:
    def __init__(self, client, host: str, password: str):
        """Initialise the Amplifi client."""
        self._client = client
        self._host = host
        self._password = password
        self._base_url = f"http://{self._host}"
        self._login_token = None
        self._info_token = None

    async def async_get_devices(self):
        """Get the default device list from the router"""
        return await self._async_get_info()

    async def _async_get_login_token(self):
        """Get the login token from the form."""
        _LOGGER.debug("[GET] '%s' - get login token" % (self._base_url + "/info.php"))
        resp = await self._client.get(self._base_url + "/login.php")
        if resp.status != 200:
            raise AmplifiClientError("Expected a response code of 200.")

        login_page_content = await resp.text()
        token_search_result = re.findall(
            r"value=\'([A-Za-z0-9]{16})\'", login_page_content
        )

        if not token_search_result:
            self._login_token = None
            raise AmplifiClientError("Login token was not found.")

        login_token = token_search_result[0]
        _LOGGER.debug("Using login_token=%s as info token" % (login_token))
        return login_token

    async def _async_login(self):
        """Login and setup a cookie based session with the router"""
        _LOGGER.debug("[POST] '%s' - logging in" % (self._base_url + "/login.php"))
        form_data = {"token": self._login_token, "password": self._password}
        resp = await self._client.post(self._base_url + "/login.php", data=form_data)
        if resp.status != 200:
            raise AmplifiClientError("Expected a response code of 200.")
        if "webui-session" not in resp.cookies:
            raise AmplifiClientError("Authentication failure.")

    async def _async_get_info_token(self):
        """Get the info token after logging in"""
        _LOGGER.debug("[GET] '%s' - get info token" % (self._base_url + "/info.php"))
        resp = await self._client.get(self._base_url + "/info.php")
        info_page_content = await resp.text()
        search_result = re.findall(r"token=\'([A-Za-z0-9]{16})\'", info_page_content)

        if resp.status != 200:
            self._info_token = None
            raise AmplifiClientError("Expected a response code of 200.")
        if not search_result:
            self._info_token = None
            raise AmplifiClientError("Login token was found.")

        info_token = search_result[0]
        _LOGGER.debug("Using token=%s as info token" % (info_token))
        return info_token

    async def _async_get_info(self):
        info_async_url = self._base_url + "/info-async.php"
        _LOGGER.debug("[GET] '%s' - get info" % (info_async_url))
        await self._async_init_client()
        form_data = {"do": "full", "token": self._info_token}
        resp = await self._client.post(info_async_url, data=form_data)

        if resp.status != 200:
            raise AmplifiClientError("Expected a response code of 200.")

        try:
            devices = await resp.json()

            # _LOGGER.debug(json.dumps(devices))
            return devices
        except (Exception) as error:
            _LOGGER.error("[GET] '%s' - failed" % (info_async_url))
            _LOGGER.error(error)
            self._handle_client_failure()
            raise AmplifiClientError("Failed to get devices from router.")

    def _handle_client_failure(self):
        self._client.cookie_jar.clear()
        self._login_token = self._info_token = None

    async def _async_init_client(self, force=False):
        if force == True or self._login_token is None or self._info_token is None:
            try:
                if force == True:
                    self._client.cookie_jar.clear()
                self._login_token = await self._async_get_login_token()
                await self._async_login()
                self._info_token = await self._async_get_info_token()
            except:
                self._login_token = self._info_token = None
                raise AmplifiClientError("Failed to init amplifi client session.")

    async def async_test_connection(self):
        """Return true when the correct host and password is provided"""
        try:
            await self._async_init_client(force=True)
            return True
        except (Exception):
            return None

    def get_router_mac_addr(self, devices):
        for device in devices[0]:
            if devices[0][device]["role"] == "Router":
                return device

    def get_wan_port_info(self, devices):
        router_mac_addr = self.get_router_mac_addr(devices)
        wan_port = devices[4][router_mac_addr]["eth-0"]
        return wan_port


# async def main():
#     # Note: Unsafe is required for aiohttp to accept cookies from an ip address
#     # see: https://docs.aiohttp.org/en/stable/client_advanced.html#cookie-jar
#     jar = aiohttp.CookieJar(unsafe=True)

#     async with aiohttp.ClientSession(cookie_jar=jar) as session:
#         amplifi = AmplifiClient(session, '192.168.0.1', 'this is not my password')
#         devices = await amplifi.async_get_info()

#         print(amplifi.get_wan_port_info(devices))


# loop = asyncio.get_event_loop()
# loop.run_until_complete(main())