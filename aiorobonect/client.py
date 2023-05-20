"""Robonect library using aiohttp."""
from __future__ import annotations

import logging
import urllib.parse

import aiohttp

from .const import TIMEOUT
from .utils import transform_json_to_single_depth

_LOGGER = logging.getLogger(__name__)


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
        params = urllib.parse.urlencode(params)
        if command == "job":
            _LOGGER.debug(f"Job params: {params}")
            return

        self.session_start()
        async with self.session.get(
            f"http://{self.host}/json?cmd={command}&{params}"
        ) as response:
            if response.status == 200:
                try:
                    result = await response.json(content_type=None)
                except Exception as e:
                    _LOGGER.error(e)
                    return False
                _LOGGER.debug("Result mower data: %s", result)
            if response.status >= 400:
                await self.session_close()
                response.raise_for_status()
        if self.transform_json:
            return transform_json_to_single_depth(result)
        return result

    async def async_cmds(self, commands=None, bypass_sleeping=False) -> list[dict]:
        """Send command to mower."""
        self.session_start()
        result = []
        result.append({"status": await self.state()})
        if not self.sleeping or bypass_sleeping:
            for cmd in commands:
                result.append({cmd: await self.async_cmd(cmd)})
        await self.session_close()
        return result

    async def state(self) -> list[dict]:
        """Send status command to mower."""
        self.session_start()
        result = await self.async_cmd("status")
        self.sleeping = result.get("status").get("status") == 17
        print(result.json)
        await self.session_close()
        return result