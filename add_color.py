import pandas as pd
import os

def add_new_color():
    file_path = 'bricklink_colors.csv'
    
    print("--- LEGO Inventory: Add New BrickLink Color ---")
    bl_id = input("Enter BrickLink ID (e.g., 151): ")
    bl_name = input("Enter BrickLink Color Name (e.g., Very Light Orange): ")
    lego_name = input("Enter LEGO Name (e.g., Light Orange): ")
    lego_id = input("Enter LEGO ID (e.g., 324): ")
    category = input("Enter Category (e.g., Solid, Transparent, Pearl): ")

    new_row = {
        'BrickLink ID': [int(bl_id)],
        'BrickLink Color Name': [bl_name],
        'LEGO Name': [lego_name],
        'LEGO ID': [int(lego_id)],
        'Category': [category]
    }
    
    new_df = pd.DataFrame(new_row)

    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        if int(bl_id) in df['BrickLink ID'].values:
            print(f"\n❌ Error: Color ID {bl_id} already exists!")
        else:
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(file_path, index=False)
            print(f"\n✅ Success! {bl_name} has been added.")
    else:
        new_df.to_csv(file_path, index=False)
        print("\n✅ Created new file and added color.")

if __name__ == "__main__":
    add_new_color()