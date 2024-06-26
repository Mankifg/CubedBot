import discord
from discord.ext import commands
from src.functions import *
import os
from supabase import create_client, Client
import supabase
from datetime import datetime as dt


url: str = os.environ.get("SUPA_URL")
key: str = os.environ.get("SUPA_KEY")

supabase: Client = create_client(url, key)

TABLE = "main"
TABLE2 = "vars"

# !!! YOU shall not run this
def delete_database(tname):
    data = supabase.table(tname).delete().execute()
    
     

def get_all_data():
    response = supabase.table(TABLE).select("*").execute()
    response = dict(response)
    response = response.get("data")
    return response


def account_with_id_exists(id: int):
    query = supabase.from_(TABLE).select("*", count="exact").eq("user_id", id)

    result = dict(query.execute())

    return result.get("count") == 1


def create_account(id):
    if account_with_id_exists(id):
        return True
    else:
        print("a")
        data = {
            "user_id": id,
            "wca_id": "",
            "data": {
                "adata": {
                    "created_at": int(dt.timestamp(dt.now())),
                    "points":0
                    },
                "solves": [],
            },
        }
        response = supabase.from_(TABLE).insert(data).execute()
        return False


def get_user_data(id):
    create_account(id)

    query = supabase.from_(TABLE).select("*", count="exact").eq("user_id", id)
    result = dict(query.execute())
    return result.get("data")[0]


def save_user_data(user_data):
    response = (
        supabase.table(TABLE)
        .update(user_data)
        .eq("user_id", user_data["user_id"])
        .execute()
    )



def load_second_table_idd(idd):
    query = supabase.from_(TABLE2).select('*', count='exact').eq('id', idd)
    result = dict(query.execute())
    return result.get('data')[0] 

def save_second_table_idd(data):
    response = supabase.table(TABLE2).update(data).eq('id', data["id"]).execute()
