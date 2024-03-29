from bs4 import BeautifulSoup
import json
import os
import requests
import sqlite3

'''
Scrapes the Apple product release data from wikipedia at the following link:
https://en.wikipedia.org/wiki/Timeline_of_Apple_Inc._products

Author: Taylor Snyder
'''

def open_database(db_name):
    '''
    Returns sqlite3 cursor and connection to specified database file db_name. Automatically creates a new DB if it doesn't exist.
    INPUT: db_name (string)
    RETURNS: cur (sqlite3 cursor), conn (sqlite3 connection)
    '''
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn

def load_JSON(filename):
    '''
    Loads in a JSON file with the given name if it exists.
    INPUTS: filename (string)
    RETURNS: Dictionary with loaded data (or empty dictionary)
    '''
    
    try:
        # Open file
        source_dir = os.path.dirname(__file__)
        full_path = os.path.join(source_dir, filename)
        infile = open(full_path, 'r')

        data = json.load(infile)
        print("Loaded in JSON file successfully.")
        return data
        
    except:
        print("Could not open JSON file, beginning process with empty dictionary.")
        return dict()

def write_JSON(filename, data):
    '''
    Writes data as a JSON to the given filename.
    INPUTS: filename (string), data (dictionary)
    RETURNS: None
    '''
    
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, indent=2)

def color_code_lookup(color_code):
    '''
    Returns the item category based on the row's background color.
    INPUT: Table Row Background Color Code (String)
    RETURNS: Item Category (String)
    '''
    
    if color_code == '#FFFF79' or color_code == 'FFFF79':
        return "Apple 1/2/2GS/3"
    elif color_code == '#81D666' or color_code == '81D666':
        return "Lisa"
    elif color_code == '#95CEFE' or color_code == '95CEFE':
        return "Macintosh"
    elif color_code == '#8BFFA3' or color_code == '8BFFA3':
        return "Network Server"
    elif color_code == '#CCFF99' or color_code == 'CCFF99' or color_code == '#CF9':
        return "Phones/Tablets/PDAs"
    elif color_code == '#FFE5E5' or color_code == 'FFE5E5':
        return "iPod/Consumer Products"
    elif color_code == '#D8D8F2' or color_code == 'D8D8F2':
        return "Computer Peripherals"
    else:
        return "N/A"

def add_25_entries(soup, data):
    '''
    Adds up to 25 entries from the provided soup into the data dictionary (if they do not exist already).
    INPUTS: soup (BS4 soup object), data (dictionary)
    RETURNS: number of entries added (integer)
    '''
    
    table_list = soup.find_all('tr', bgcolor=True)
    
    # Placeholders for rowspans in table, entries counter
    rowspan = 0
    rowspan_date = ""
    entries_added = 0
    
    for row in table_list:
        
        row_data = row.find('td')
        row_name = row.find('a')
        
        # Lookup category with bg color code
        row_category = color_code_lookup(row['bgcolor'].rstrip().upper())
        
        
        if row_data:
            # First, check to see if the row has a row span
            if row_data.has_attr('rowspan'):
                rowspan = int(row_data['rowspan'])
                rowspan_date = row_data.text.rstrip()
            
            # If we have rowspan, decrement and use rowspan date until rowspan is complete
            if rowspan != 0:
                entry_name = row_name.text.rstrip()
                entry_details = {
                                "release date" : rowspan_date,
                                "category"     : row_category
                                }
                rowspan -= 1
                
            else:
                entry_name = row_name.text.rstrip()
                entry_details = {
                                "release date" : row_data.text.rstrip(),
                                "category"     : row_category
                                }
            
            # No duplicates
            if data.get(entry_name) is None:
                data[entry_name] = entry_details
                entries_added += 1
                
        
        # Check that we do not add more than 25 things per run
        if entries_added >= 25:
            break        
    
    return entries_added
    
def add_entries_to_JSON():
    '''
    Loads JSON data, sends a request to the wikipedia URL, creates the soup object, adds entries, and writes to updated JSON.
    INPUTS: None
    RETURNS: data (dictionary) with new entries appended if found
    '''
    
    data = load_JSON("apple_products.json")
    
    r = requests.get('https://en.wikipedia.org/wiki/Timeline_of_Apple_Inc._products')
    
    if not r.ok:
        print("Error, unable to connect to url.")
        
    soup = BeautifulSoup(r.content, 'html.parser')
    
    num_entries_added = add_25_entries(soup, data)
    
    write_JSON("apple_products.json", data)
    
    print(f"Added {num_entries_added} entries to the database and JSON.")
    
    return data

def SQL_create_categories(cur, conn):
    '''
    Create the Apple_Categories table which links an ID to the category of the product. Should be used as a foreign key in Apple_Products.
    INPUTS: cur (sqlite3 cursor), conn (sqlite3 connection)
    RETURNS: None
    '''
    
    categories = ["Apple 1/2/2GS/3", "Lisa", "Macintosh", "Network Server", "Phones/Tablets/PDAs", "iPod/Consumer Products", "Computer Peripherals"]
    
    cur.execute("CREATE TABLE IF NOT EXISTS Apple_Categories (id INTEGER PRIMARY KEY, category TEXT UNIQUE)")
    
    for i in range(len(categories)):
        cur.execute("INSERT OR IGNORE INTO Apple_Categories (id, category) VALUES (?,?)", (i, categories[i]))
        
    conn.commit()

def SQL_update_database(cur, conn, data):
    '''
    Updates the database with any new entries in the JSON data. Finds the associated category_id from Apple_Categories to reference as foreign key.
    INPUTS: cur (sqlite3 cursor), conn (sqlite3 connection), data (dicitonary)
    '''
    
    cur.execute("CREATE TABLE IF NOT EXISTS Apple_Products (id INTEGER PRIMARY KEY, name TEXT UNIQUE, release_date TEXT, category INTEGER)")
    
    for product_name in data:
        release_date = data[product_name]['release date']
        category_string = data[product_name]['category']
        
        cur.execute("SELECT id FROM Apple_Categories WHERE category = (?)", (category_string,))
        
        category_id = cur.fetchone()[0]
        
        cur.execute("INSERT OR IGNORE INTO Apple_Products (name, release_date, category) VALUES (?,?,?)", (product_name, release_date, category_id))
    
    conn.commit()

def main():
    '''
    Driver function which ensures that each time the program is run, the JSON is updated with <= 25 new entries, and that the SQL database is then also updated.
    INPUTS: None
    RETURNS: None
    '''
    cur, conn = open_database('Apptendo.db')
    
    SQL_create_categories(cur, conn)
    
    data = add_entries_to_JSON()
    
    SQL_update_database(cur, conn, data)
    
if __name__ == '__main__':
    main()