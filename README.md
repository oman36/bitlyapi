# bitlyapi

## Example:

```python
import asyncio

from bitlyapi.api import BitlyAPI
from bitlyapi.exceptions import APIException


async def main():
    credentials = {
        'username': '',
        'password': '',
        'client_id': '',
        'client_secret': '',
        # 'token': '',
    }
    async with BitlyAPI(**credentials) as api:
        responses = await asyncio.gather(
            api.link.clicks(link='https://bit.ly/2EAh3Vo'),
            api.link.clicks(link='2A7lTGn'),
        )
        for response in responses:
            print(response.link_clicks)  # output: <number of clicks>
        try:
            response = await api.link.clicks(link='bad_link')
        except APIException as err:
            print(err)  # output: [404] NOT FOUND


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
```
