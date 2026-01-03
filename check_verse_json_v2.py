
import json

def check_verse():
    try:
        with open('Valmiki_Ramayan_Shlokas.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        max_shloka = 0
        found_sarga = False
        
        for item in data:
            kanda = item.get('kanda', '').strip()
            sarga = item.get('sarga')
            shloka = item.get('shloka') or item.get('verse_number')
            
            if 'Aranya' in kanda and str(sarga) == '27':
                found_sarga = True
                try:
                    s_num = int(shloka)
                    if s_num > max_shloka:
                        max_shloka = s_num
                except:
                    pass

        if found_sarga:
            print(f"Aranya Kanda Sarga 27 found. Max shloka number is: {max_shloka}")
        else:
            print("Aranya Kanda Sarga 27 NOT found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_verse()
