"""FastAPI backend exposing the Diplomacy adjudicator to the GitHub Pages frontend."""
import os
import threading
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game import web_api

MAX_GAMES = 200

app = FastAPI(title='Diplomacy Adjudicator')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get('ALLOWED_ORIGINS', '*').split(',')],
    allow_methods=['*'],
    allow_headers=['*'],
)

_games = {}
_lock = threading.Lock()


class OrderRequest(BaseModel):
    order: str
    power: str


class DrawRequest(BaseModel):
    power: str


def _get(game_id):
    game = _games.get(game_id)
    if game is None:
        raise HTTPException(404, 'Unknown game id')
    return game


def _check_power(game, power):
    if game.game_state.get_player(power) is None:
        raise HTTPException(400, f'Unknown power: {power}')


@app.get('/health')
def health():
    return {'ok': True}


@app.post('/games')
def create_game():
    with _lock:
        if len(_games) >= MAX_GAMES:
            _games.pop(next(iter(_games)))
        game_id = uuid.uuid4().hex
        _games[game_id] = web_api.new_game()
    return {'game_id': game_id, 'state': web_api.get_state(_games[game_id])}


@app.get('/games/{game_id}')
def get_state(game_id: str):
    return web_api.get_state(_get(game_id))


@app.post('/games/{game_id}/orders')
def submit_order(game_id: str, req: OrderRequest):
    game = _get(game_id)
    with _lock:
        result = web_api.submit_order(game, req.order, req.power)
        result['state'] = web_api.get_state(game)
    return result


@app.post('/games/{game_id}/resolve')
def resolve(game_id: str):
    game = _get(game_id)
    with _lock:
        return web_api.resolve(game)


@app.post('/games/{game_id}/draw')
def draw(game_id: str, req: DrawRequest):
    game = _get(game_id)
    _check_power(game, req.power)
    with _lock:
        return web_api.draw(game, req.power)
