import asyncio
from time import sleep, time
import os
from threading import Thread
from typing import Union

from aiohttp import request, ClientSession
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    #Get the session
    global session
    global token
    session = ClientSession()
    token = await authenticate(session)
    yield
    # Clean up the ML models and release the resources
    await session.close()

app = FastAPI(lifespan=lifespan)
session = None
token = None

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/playlist")
async def playlist( id: str):
    print(token)
    headers = {
        'Authorization': 'Bearer ' + token
    }
    try:
        if id:
            async with session.get(f"https://api.spotify.com/v1/playlists/{id}?fields=tracks.items(track(name, album(artists)))", headers=headers) as response:
                if response.status == 200:
                    #must return name of playlist and its tracks (name, artists list)
                    #currently only returns 100 songs for some reason
                    songs = {}
                    result = await response.json()

                    for i in range (len(result['tracks']['items'])):
                        print(result['tracks']['items'][i])
                        songs[(result['tracks']['items'][i]['track']['name'])] = []

                        localArtists = []
                        for artist in result['tracks']['items'][i]['track']['album']['artists']:
                            localArtists.append(artist['name'])

                        songs[(result['tracks']['items'][i]['track']['name'])].append(localArtists)  

                    return (songs)
                else:
                    return ("Error fetching playlist data " + str(response.text), 500)
        else:
            return ("Error, no id specified", 500)
    except Exception as e:
        return e

@app.post("/authenticate")
async def authenticate(session):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'client_id': os.environ['SPOTIFY_API_CLIENT_ID'],
        'client_secret': os.environ['SPOTIFY_API_CLIENT_SECRET']
    }
    async with session.post("https://accounts.spotify.com/api/token", data=data) as response:
        print(response.status)
        cookie = await response.json()
        return cookie['access_token']



        
# # thread to regenerate tokens every 30 minutes (implement when using web app)
# def reauth():
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     while True:
#         loop.run_until_complete(authenticate(session))
#         time.sleep(30 * 60) # Sleep for half an hour, then re-authenticate

# # Start the thread
# t = Thread(target=reauth)
# t.start()