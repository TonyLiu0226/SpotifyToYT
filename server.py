import asyncio
from time import sleep, time
import os
from threading import Thread
from typing import Union

from aiohttp import request, ClientSession
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from ytmusicapi import YTMusic

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
ytmusic = YTMusic("oauth.json")
session = None
token = None

async def createPlayList(name):
    try:
        result = ytmusic.create_playlist(title=name, description="")
        return result
    except Exception as e:
        print(e)

async def searchSongByNameAndArtist(name, artist):
    try:
        result = ytmusic.search(query=f"${name} by ${artist}", filter="songs")
        print(result[0])
        return result[0]
    except Exception as e:
        print(e)

async def addSongToPlaylist(playlistId, videoId):
    try:
        result = ytmusic.add_playlist_items(playlistId=playlistId, videoIds=[videoId])
        print(result)
    except Exception as e:
        print(e)

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
            async with session.get(f"https://api.spotify.com/v1/playlists/{id}?fields=name,tracks.items(track(name, album(artists)))", headers=headers) as response:
                if response.status == 200:
                    #must return name of playlist and its tracks (name, artists list)
                    #currently only returns 100 songs for some reason
                    songs = {}
                    result = await response.json()
                    name = result["name"]

                    for i in range (len(result['tracks']['items'])):
                        songs[(result['tracks']['items'][i]['track']['name'])] = []

                        localArtists = []
                        for artist in result['tracks']['items'][i]['track']['album']['artists']:
                            localArtists.append(artist['name'])

                        songs[(result['tracks']['items'][i]['track']['name'])].append(localArtists)  

                    playlistId = await createPlayList(name)

                    for song in songs.keys():
                        result = await searchSongByNameAndArtist(song, songs[song])
                        final = await addSongToPlaylist(playlistId, result['videoId'])
                        print(final)

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