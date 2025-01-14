"""Robonect library using aiohttp."""
from __future__ import annotations

import json
import logging
import urllib.parse

import aiohttp

from .const import TIMEOUT
from .utils import transform_json_to_single_depth

_LOGGER = logging.getLogger(__name__)


def encode_dict_values_to_utf8(dictionary):
    encoded_dict = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            encoded_dict[key] = encode_dict_values_to_utf8(value)
        elif isinstance(value, str):
            encoded_dict[key] = value.encode("utf-8")
        else:
            encoded_dict[key] = value
    return encoded_dict


def validate_json(json_str):
    """Validate json string."""
    if type(json_str) is dict:
        return True
    try:
        return json.loads(json_str)
    except ValueError as error:
        print(error)
        return False


class RobonectException(Exception):
    """Raised when an update has failed."""


class RobonectClient:
    """Class to communicate with the Robonect API."""

    def __init__(self, host, username, password, transform_json=False) -> None:
        """Initialize the Communication API to get data."""
        self.auth = None
        self.host = host
        self.username = username
        self.password = password
        self.session = None
        self.sleeping = None
        self.transform_json = transform_json
        if username is not None and password is not None:
            self.auth = aiohttp.BasicAuth(login=username, password=password)

    def session_start(self):
        """Start the aiohttp session."""
        if self.session:
            return True
        if self.username is not None and self.password is not None:
            self.session = aiohttp.ClientSession(read_timeout=TIMEOUT, auth=self.auth)
            return True
        return False

    async def session_close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
        self.session = None

    async def async_cmd(self, command=None, params={}) -> list[dict]:
        """Send command to mower."""
        if command is None:
            return False
        if params is None:
            params = ""
        else:
            params = urllib.parse.urlencode(params)

        if command == "job":
            _LOGGER.debug(f"Job params: {params}")
            return

        self.session_start()
        try:
            async with self.session.get(
                f"http://{self.host}/json?cmd={command}&{params}"
            ) as response:
                if response.status == 200:
                    result = await response.json(encoding="iso-8859-1")
                    _LOGGER.debug("Result mower data: %s", result)
                if response.status >= 400:
                    await self.session_close()
                    response.raise_for_status()
            await self.session_close()
            if self.transform_json:
                return transform_json_to_single_depth(result)
            return result
        except Exception as exception:
            await self.session_close()
            raise exception

    async def async_cmds(self, commands=None, bypass_sleeping=False) -> dict:
        """Send command to mower."""
        self.session_start()
        result = await self.state()
        if result:
            result = {"status": result}
            if not self.sleeping or bypass_sleeping:
                for cmd in commands:
                    result.update({cmd: await self.async_cmd(cmd)})
            await self.session_close()
        return result

    async def state(self) -> dict:
        """Send status command to mower."""
        self.session_start()
        result = await self.async_cmd("status")
        if result:
            self.sleeping = result.get("status").get("status") == 17
            await self.session_close()
        return result

    async def async_start(self) -> bool:
        """Start the mower."""
        return await self.async_cmd("start")

    async def async_stop(self) -> bool:
        """Stop the mower."""
        return await self.async_cmd("stop")

    async def async_reboot(self) -> bool:
        """Reboot Robonect."""
        return await self.async_cmd("service", {"service": "reboot"})

    async def async_shutdown(self) -> bool:
        """Shutdown Robonect."""
        return await self.async_cmd("service", {"service": "shutdown"})

    async def async_sleep(self) -> bool:
        """Make Robonect sleep."""
        return await self.async_cmd("service", {"service": "sleep"})

    def sleeping(self) -> int:
        """Return if the mower is sleeping."""
        return self.sleeping
