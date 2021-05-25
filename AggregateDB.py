import mariadb
from misc import trc_mean

def getConnDB():
    conn= None
    try:
        conn = mariadb.connect(
            user="root",
            password="!Gkrrhkwkd0690",
            host="220.149.87.248",
            port=3307,
            database="livfarm"

        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)
    return(conn);


# Get Cursor
conn = getConnDB()
