import os
import time
import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from datetime import datetime


"""################ Prerequisites ################"""
# pip3 install aiohttp
# pip3 install asyncio
# pip3 install bs4



"""################ Settings ################"""
#directory = "/Users/username/Documents/EVE/logs/Gamelogs"  #MacOS
#directory = r"C:\Users\UserName\Documents\EVE\logs\Gamelogs"   #Windows
directory = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "Logs", "Gamelogs")
  

victoriametrics_url = " http://0.0.0.0:8428/influx/write" # Adjust URL as needed
username = "username"
password = "password"
hours = 1  #filter for logs
measurement="ATXXI" #prefix 
language="english"   #   english   russian   french   german   japanese   chinese
debug=False
debug_post=True
send_post_query=True
marker = "(combat)" # do not change

"""################ Templates for parsing ################"""

capNeutralizedOutColor = "<color=0xff7fffff>"  #your actions
capNeutralizedInColor = "<color=0xffe57f7f>"   #action towards you
DamageRegex = r"-\s*([^-\r\n]+?)\s*-\s*"
OtherRegex = r"-\s*([^<]+)</font>\s*$"
DamageMask_amount = 0
DamageMask_ship = 1
DamageMask_pilot = 1
OtherMask_amount = 0
OtherMask_ship = 2
OtherMask_pilot = 3

"""################ Patterns ################"""

_logLanguageXML = {
    'english': {
        'listener': "Listener",
        'damageOut': ">to<",
        'damageIn': ">from<",
        'armorRepairedOut': "> remote armor repaired to <",
        'hullRepairedOut': "> remote hull repaired to <",
        'shieldBoostedOut': "> remote shield boosted to <",
        'armorRepairedIn': "> remote armor repaired by <",
        'hullRepairedIn': "> remote hull repaired by <",
        'shieldBoostedIn': "> remote shield boosted by <",
        'capTransferedOut': "> remote capacitor transmitted to <",
        'capNeutralizedOut': "> energy neutralized <",
        'nosRecieved': "> energy drained from <",
        'capTransferedIn': "> remote capacitor transmitted by <",
        'capNeutralizedIn': "> energy neutralized <",
        'nosTaken': "> energy drained to <"
    },
    'russian': {
        'listener': "Слушатель",        
        'damageOut': ">на<",
        'damageIn': ">из<",
        'armorRepairedOut': "> единиц запаса прочности брони отремонтировано <",
        'hullRepairedOut': "> единиц запаса прочности корпуса отремонтировано <",
        'shieldBoostedOut': "> единиц запаса прочности щитов накачано <",
        'armorRepairedIn': "> единиц запаса прочности брони получено дистанционным ремонтом от <",
        'hullRepairedIn': "> единиц запаса прочности корпуса получено дистанционным ремонтом от <",
        'shieldBoostedIn': "> единиц запаса прочности щитов получено накачкой от <",
        'capTransferedOut': "> единиц запаса энергии накопителя отправлено в <",
        'capNeutralizedOut': "> энергии нейтрализовано <",
        'nosRecieved': "> энергии извлечено из <",
        'capTransferedIn': "> единиц запаса энергии накопителя получено от <",
        'capNeutralizedIn': "> энергии нейтрализовано <",
        'nosTaken': "> энергии извлечено и передано <"
    },
    'french': {
        'listener': "Auditeur",        
        'damageOut': ">à<",
        'damageIn': ">de<",
        'armorRepairedOut': "> points de blindage transférés à distance à <",
        'hullRepairedOut': "> points de structure transférés à distance à <",
        'shieldBoostedOut': "> points de boucliers transférés à distance à <",
        'armorRepairedIn': "> points de blindage réparés à distance par <",
        'hullRepairedIn': "> points de structure réparés à distance par <",
        'shieldBoostedIn': "> points de boucliers transférés à distance par <",
        'capTransferedOut': "> points de capaciteur transférés à distance à <",
        'capNeutralizedOut': "> d'énergie neutralisée en faveur de <",
        'nosRecieved': "> d'énergie siphonnée aux dépens de <",
        'capTransferedIn': "> points de capaciteur transférés à distance par <",
        'capNeutralizedIn': "> d'énergie neutralisée aux dépens de <",
        'nosTaken': "> d'énergie siphonnée en faveur de <"
    },
    'german': {
        'listener': "Empfänger",    
        'damageOut': ">nach<",
        'damageIn': ">von<",
        'armorRepairedOut': "> Panzerungs-Fernreparatur zu <",
        'hullRepairedOut': "> Rumpf-Fernreparatur zu <",
        'shieldBoostedOut': "> Schildfernbooster aktiviert zu <",
        'armorRepairedIn': "> Panzerungs-Fernreparatur von <",
        'hullRepairedIn': "> Rumpf-Fernreparatur von <",
        'shieldBoostedIn': "> Schildfernbooster aktiviert von <",
        'capTransferedOut': "> Fernenergiespeicher übertragen zu <",
        'capNeutralizedOut': "> Energie neutralisiert <",
        'nosRecieved': "> Energie transferiert von <",
        'capTransferedIn': "> Fernenergiespeicher übertragen von <",
        'capNeutralizedIn': "> Energie neutralisiert <",
        'nosTaken': "> Energie transferiert zu <"
    },
    'japanese': {
        'listener': "傍聴者",          
        'damageOut': ">対象:<",
        'damageIn': ">攻撃者:<",
        'armorRepairedOut': "> remote armor repaired to <",
        'hullRepairedOut': "> remote hull repaired to <",
        'shieldBoostedOut': "> remote shield boosted to <",
        'armorRepairedIn': "> remote armor repaired by <",
        'hullRepairedIn': "> remote hull repaired by <",
        'shieldBoostedIn': "> remote shield boosted by <",
        'capTransferedOut': "> remote capacitor transmitted to <",
        'capNeutralizedOut': "> エネルギーニュートラライズ 対象:<",
        'nosRecieved': "> エネルギードレイン 対象:<",
        'capTransferedIn': "> remote capacitor transmitted by <",
        'capNeutralizedIn': ">のエネルギーが解放されました<",
        'nosTaken': "> エネルギードレイン 攻撃者:<"
    },
    'chinese':{
        'listener': "收听者",
        'damageOut': ">对<",
        'damageIn': ">来自<",
        'armorRepairedOut': ">远程装甲维修量至<",
        'hullRepairedOut': ">远程结构维修量至<",
        'shieldBoostedOut': ">远程护盾回充增量至<",
        'armorRepairedIn': ">远程装甲维修量由<",
        'hullRepairedIn': ">远程结构维修量由<",
        'shieldBoostedIn': ">远程护盾回充增量由<",
        'capTransferedOut': ">远程电容传输至<",
        'capNeutralizedOut': ">能量中和<",
        'nosRecieved': ">被从<",
        'capTransferedIn': ">远程电容传输量由<",
        'capNeutralizedIn': ">能量中和<",
        'nosTaken': ">被吸取到<"
        } 
}

_LanguageFilter = {
    'english': {
        0: ">Warp scramble attempt<",
        1: ">Warp disruption attempt<"
    },
    'russian': {

    },
    'french': {

    },
    'german': {

    },
    'japanese': {

    },
    'chinese':{

        } 
}

"""################ Functions ################"""

   
def get_recent_logs(directory, hours):
    """Returns a list of logs that were modified no earlier than N hours ago"""
    now = time.time()
    threshold = now - hours * 3600
    recent_logs = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath) and filepath.endswith('.txt'):
            mtime = os.path.getmtime(filepath)
            if mtime >= threshold:
                recent_logs.append((filepath, mtime))
    return recent_logs

def extract_header(log_path):
    """Extracts the log header"""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            delimiter_count = 0
            header_lines = []
            for line in lines:
                if '------------------------------------------------------------' in line:
                    delimiter_count += 1
                    if delimiter_count >= 2:
                        break
                elif delimiter_count < 2:
                    ind = line.find(_logLanguageXML[language]["listener"])
                    if ind != -1:
                        value = line[ind+10:]
                        header_lines.append(value)
                    ind_2 = line.find("Session Started:")
                    if ind_2 != -1:
                        value = line[ind_2+17:]
                        header_lines.append(value)
            
            return ' - '.join(header_lines)
    except Exception as e:
        return f"Error: {str(e)}"
        
        
async def send_influxdb_metric(session, tags, field, value):
    """ Sends a single metric in InfluxDB line protocol format to VictoriaMetrics"""
    tag_string = ','.join([f'{k}={v}' for k, v in tags.items()])
    payload = f'{measurement},{tag_string} {field}={value}' #{timestamp_ns}'
    auth_tuple = aiohttp.BasicAuth(username, password)
    headers = {'Content-Type': 'text/plain'}
    try:
        if debug_post:
            print( payload  )
        async with session.post(victoriametrics_url, data=payload, headers=headers, auth=auth_tuple) as response:
            if response.status != 204:
                print(f"Error: ... (Status: {response.status})")
    except Exception as e:
        print(f"Error: {e}")


def is_number(string):
    pattern = r'^-?\d+\.?\d*$'  # Integers and real numbers
    return bool(re.fullmatch(pattern, string))
        

async def process_log_line_xml(session, line, my_char):
    if not line.strip():
        return
    if marker in line:
       line = line.split(marker, 1)[1]
       line = line.strip()
       soup = BeautifulSoup(line, "html.parser")
       if debug:
          print(line) 
          print(soup)
    else:
        return
        
    jsondata = { 
       "type": [],
       "amount": [],
       "pilotName": [],
       "shipType": [],
       "weaponType": [],
    }
    
########## Simple Filter
    for i in range(len(_LanguageFilter[language])):
       if _LanguageFilter[language][i] in line:
          return
    
    
########## DAMAGE

    if _logLanguageXML[language]["damageOut"] in line:
       if debug:
          print("damageOut") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[DamageMask_amount] if len(b_tags) > DamageMask_amount else None
       ship   = b_tags[DamageMask_ship] if len(b_tags) > DamageMask_ship else None
       pilot  = b_tags[DamageMask_pilot] if len(b_tags) > DamageMask_pilot else None
       ship = ship.rsplit("(", 1)[1].rstrip(")") 
       pilot = pilot.split("[", 1)[0]
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(DamageRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("damageOut")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

    if _logLanguageXML[language]["damageIn"] in line:
       if debug:
          print("damageIn") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[DamageMask_amount] if len(b_tags) > DamageMask_amount else None
       ship   = b_tags[DamageMask_ship] if len(b_tags) > DamageMask_ship else None
       pilot  = b_tags[DamageMask_pilot] if len(b_tags) > DamageMask_pilot else None
       ship = ship.rsplit("(", 1)[1].rstrip(")") 
       pilot = pilot.split("[", 1)[0]
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(DamageRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("damageIn")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)
 
########## LOGI OUT
 
    if _logLanguageXML[language]["shieldBoostedOut"] in line:
       if debug:
          print("shieldBoostedOut") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("shieldBoostedOut")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

    if _logLanguageXML[language]["armorRepairedOut"] in line:
       if debug:
          print("armorRepairedOut") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("armorRepairedOut")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

    ## hull not tested
    if _logLanguageXML[language]["hullRepairedOut"] in line:
       if debug:
          print("hullRepairedOut") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("hullRepairedOut")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

 ########## LOGI IN
 
    if _logLanguageXML[language]["shieldBoostedIn"] in line:
       if debug:
          print("shieldBoostedIn") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("shieldBoostedIn")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

    if _logLanguageXML[language]["armorRepairedIn"] in line:
       if debug:
          print("armorRepairedIn")            
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("armorRepairedIn")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

    ## hull not tested
    if _logLanguageXML[language]["hullRepairedIn"] in line:
       if debug:
          print("hullRepairedIn") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("hullRepairedIn")
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)

########## Energy Neutralziers

    if (_logLanguageXML[language]["capNeutralizedOut"] in line and capNeutralizedOutColor in line):
       if debug:
          print("capNeutralizedOut") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("capNeutralizedOut")
       amount = "".join(ch for ch in amount if ch.isdigit())
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)


    if (_logLanguageXML[language]["capNeutralizedIn"] in line and capNeutralizedInColor in line):
       if debug:
          print("capNeutralizedIn")
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("capNeutralizedIn")
       amount = "".join(ch for ch in amount if ch.isdigit())
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)


########## Energy Neutralziers


    if _logLanguageXML[language]["nosRecieved"] in line:
       if debug:
          print("nosRecieved")              
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("nosRecieved")
       amount = "".join(ch for ch in amount if ch.isdigit())
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)
       
       
    if _logLanguageXML[language]["nosTaken"] in line:
       if debug:
          print("nosTaken") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("nosTaken")
       amount = "".join(ch for ch in amount if ch.isdigit())
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)
       

########## Energy Transfers


    if _logLanguageXML[language]["capTransferedOut"] in line:
       if debug:
          print("capTransferedOut") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("capTransferedOut")
       amount = "".join(ch for ch in amount if ch.isdigit())
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)
 

    if _logLanguageXML[language]["capTransferedIn"] in line:
       if debug:
          print("capTransferedIn") 
       b_tags = [b.get_text(strip=True) for b in soup.find_all("b")]       
       amount = b_tags[OtherMask_amount] if len(b_tags) > OtherMask_amount else None
       ship   = b_tags[OtherMask_ship] if len(b_tags) > OtherMask_ship else None
       pilot  = b_tags[OtherMask_pilot] if len(b_tags) > OtherMask_pilot else None
       if debug:
          for b in soup.find_all("b"):
             print(b.get_text(strip=True))
       weapon = None
       match = re.search(OtherRegex, line)
       if match:
          weapon = match.group(1).strip()
       jsondata["type"].append("capTransferedIn")
       amount = "".join(ch for ch in amount if ch.isdigit())
       jsondata["amount"].append(amount)
       jsondata["pilotName"].append(pilot)
       jsondata["shipType"].append(ship)
       jsondata["weaponType"].append(weapon)
       


 

    if debug:
       print(jsondata) 
    if (send_post_query and len(jsondata["type"])>0):
       await send_influxdb_metric( session=session, tags={"char": my_char.replace(" ","\\ "), "pilotName": jsondata["pilotName"][0].replace(" ","\\ "), "shipType": jsondata["shipType"][0].replace(" ","\\ "), "weaponType": jsondata["weaponType"][0].replace(" ","\\ ")}, field=jsondata["type"][0], value=jsondata["amount"][0] )



 
async def async_main():
    print("     ")
    print("     VER 2.03 23.08.2025")
    print("     ")
    
    #hours = int(input("Enter the maximum age of logs in hours (N): "))
    logs = get_recent_logs(directory, hours)
    if not logs:
        print("No matching logs found.")
        return
      
    logs.sort(key=lambda x: x[1], reverse=True)
    
    print("\nAvailable logs (not older than {} hours):".format(hours))
    for i, (log_path, mtime) in enumerate(logs, 1):
        header = extract_header(log_path)
        first_line = header if header else "No header"
        date_str = datetime.fromtimestamp(mtime).strftime('%Y.%m.%d %H:%M:%S')
        print(f"{i} - {first_line}")
    
    choice = int(input("\nSelect log number (0 to exit): "))
    if 1 <= choice <= len(logs):
        selected_log = logs[choice-1][0]
        print(f"\nStart:\n")
        my_char = ""
        with open(selected_log, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                ind = line.find(_logLanguageXML[language]["listener"]+":")
                if ind != -1:
                    my_char = line[ind+10:]
                    my_char = my_char.strip()
        file_size = os.path.getsize(selected_log)    
        last_position = file_size
        #last_position = 0
        
        async with aiohttp.ClientSession() as session:
        
            while True:
                try:
                    file_size = os.path.getsize(selected_log)
                    if file_size < last_position:
                        last_position = 0
                    if file_size > last_position:
                        with open(selected_log, 'r') as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            last_position = f.tell()
                            for line in new_lines:
                                await process_log_line_xml(session, line.strip(), my_char)
                except Exception as e:
                    print(f"Error reading file: {e}")
                await asyncio.sleep(50/1000)
    elif choice != 0:
        print("Wrong choice.")
        
        
def main():
    asyncio.run(async_main())
if __name__ == "__main__":
    main()





