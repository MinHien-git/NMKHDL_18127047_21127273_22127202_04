import pandas as pd
import requests
import tempfile
import os

def download_excel(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        with open(temp_file.name, 'wb') as file:
            file.write(response.content)
        print("File downloaded successfully.")
        return temp_file.name
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        return None

def extract_to_csv(excel_path, output_csv):
    excel_data = None
    try:
        excel_data = pd.ExcelFile(excel_path)
        combined_data = pd.DataFrame()
        
        for sheet_name in excel_data.sheet_names:
            # Load sheet and skip rows until headers
            df = excel_data.parse(sheet_name, skiprows=6)

            print("Crawling...", sheet_name)
            # Check if DataFrame has the expected number of columns
            if df.shape[1] < 6:  # Fewer columns than expected
                print(f"Skipping sheet '{sheet_name}' - Fewer columns than expected.")
                continue
            
            # Rename columns if they match the expected structure
            df.columns = df.columns[:6].tolist() + ['extra_column' for _ in range(df.shape[1] - 6)]
            df = df.rename(columns={df.columns[1]: 'TÊN ĐƯỜNG', df.columns[5]: 'Giá đất đề nghị điều chỉnh'})
            
            # Drop rows without a street name
            df = df.dropna(subset=['TÊN ĐƯỜNG'])
            
            # Convert 'Giá đất đề nghị điều chỉnh' to numeric, coerce errors
            df['Giá đất đề nghị điều chỉnh'] = pd.to_numeric(df['Giá đất đề nghị điều chỉnh'], errors='coerce')
            
            # Drop rows with NaN values in 'Giá đất đề nghị điều chỉnh' after conversion
            df = df.dropna(subset=['Giá đất đề nghị điều chỉnh'])
            
            # Add district column
            df['QUẬN'] = sheet_name
            
            # Clone "THỦ ĐỨC" to "Quận 2" and "Quận 9"
            if 'THỦ ĐỨC' in df['QUẬN'].values:
                df_2 = df[df['QUẬN'] == 'Thủ Đức'].copy()
                df_2['QUẬN'] = 'Quận 2'  # Clone for Quận 2
                df_9 = df[df['QUẬN'] == 'Thủ Đức'].copy()
                df_9['QUẬN'] = 'Quận 9'  # Clone for Quận 9
                df = pd.concat([df, df_2, df_9], ignore_index=True)
            
            # Select relevant columns and ignore extra columns
            df_filtered = df[['TÊN ĐƯỜNG', 'Giá đất đề nghị điều chỉnh', 'QUẬN']]
            combined_data = pd.concat([combined_data, df_filtered], ignore_index=True)
        
        if not combined_data.empty:
            # Group by 'TÊN ĐƯỜNG' and 'District' and calculate the mean of 'Giá đất đề nghị điều chỉnh'
            aggregated_data = combined_data.groupby(['TÊN ĐƯỜNG', 'QUẬN'], as_index=False)['Giá đất đề nghị điều chỉnh'].mean()
            
            # Sort the aggregated data by 'District' and then by 'Giá đất đề nghị điều chỉnh' in descending order
            aggregated_data = aggregated_data.sort_values(by=['QUẬN', 'Giá đất đề nghị điều chỉnh'], ascending=[True, False])
            
            # Save the sorted aggregated data to the CSV file
            aggregated_data.to_csv(output_csv, index=False)
            print(f"Data saved to {output_csv}")
        else:
            print("No data found with the specified columns.")
    except ImportError as e:
        print("Missing required module. Please install the required module and try again.")
        print(f"Error: {e}")
    finally:
        if excel_data is not None:
            excel_data.close()  # Ensure the file is closed after reading

def main():
    url = "https://xdcs.cdnchinhphu.vn/446259493575335936/2024/10/22/phu-luc-bang-8-bgd-dat-o-1-1729562018876764836390-1-17295692360131820457301.xlsx"
    output_csv = "gbd.csv"
    
    excel_path = download_excel(url)
    if excel_path:
        try:
            extract_to_csv(excel_path, output_csv)
        finally:
            os.remove(excel_path)  # Clean up the file

if __name__ == "__main__":
    main()
