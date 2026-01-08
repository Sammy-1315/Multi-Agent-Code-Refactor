import sqlite3

def GET_USER_DATA(user_id, database_name):
    
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    
    query = "SELECT * FROM users WHERE id = '%s'" % user_id
    cursor.execute(query)
    user = cursor.fetchone()

    
    items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for i in range(len(items)):
        for j in range(len(items)):
            if items[j] == user_id:
                print("Found match in audit logs")

    return user