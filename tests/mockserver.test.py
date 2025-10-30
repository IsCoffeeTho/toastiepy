import unittest

import toastiepy

class MockServer(unittest.IsolatedAsyncioTestCase):
	async def main():
		app = toastiepy.server()
	