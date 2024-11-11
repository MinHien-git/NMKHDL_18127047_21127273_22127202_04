import pandas as pd

# Load the uploaded property listing CSV file
file_path = './property_listings.csv'  # Replace with your actual property listing file path
df = pd.read_csv(file_path)

# Clean 'Diện tích' column
df['Diện tích'] = df['Diện tích'].str.replace(' m²', '').str.replace(',', '').astype(float)

# Drop 'Price per m2' column
df = df.drop(columns=['Price per m2'])
df = df.drop(columns=['Title'])

# Define the columns to check for null values
columns_to_check = ['Project Title', 'Status', 'Number of Apartments', 'Number of Buildings', 'Developer']

# Update rows where all specified columns are null
df.loc[df[columns_to_check].isnull().all(axis=1), ['Developer', 'Status']] = ['cá nhân/môi giới', 'Đã bàn giao']

# Remove duplicates based on 'Mã tin'
df = df.drop_duplicates(subset=['Mã tin'])

# Step 1: Load the gbd.csv file to map street names and districts
gbd_path = './gbd.csv'  # Replace with the actual path to your gbd.csv
df_gbd = pd.read_csv(gbd_path)

# Convert 'Tên đường' and 'District' columns in gbd.csv to lowercase for easier matching
df_gbd['Tên đường'] = df_gbd['TÊN ĐƯỜNG'].str.lower()
df_gbd['District'] = df_gbd['District'].str.lower()

# Function to check if an address contains the district and "Hồ Chí Minh"
def contains_hcm_and_district(address, district):
    return district.lower() in address.lower() and 'hồ chí minh' in address.lower()

# Function to calculate average 'Giá đất đề nghị điều chỉnh' by district
def calculate_avg_district_prices(df_gbd):
    district_avg_prices = {}

    # Group by district and calculate the average of 'Giá đất đề nghị điều chỉnh'
    for district in df_gbd['District'].unique():
        # Filter data for the district
        district_data = df_gbd[df_gbd['District'] == district]
        
        # Ensure 'Giá đất đề nghị điều chỉnh' is numeric and calculate the average
        district_data['Giá đất đề nghị điều chỉnh'] = pd.to_numeric(district_data['Giá đất đề nghị điều chỉnh'], errors='coerce')
        
        # Calculate the average price for the district
        avg_price = district_data['Giá đất đề nghị điều chỉnh'].mean()
        district_avg_prices[district] = avg_price

    return district_avg_prices

# Calculate the average prices for each district
district_avg_prices = calculate_avg_district_prices(df_gbd)

# Print the district average prices (for debugging purposes)
print(district_avg_prices)

# Step 2: Assign the district price to the property listing based on address matching
def assign_district_price(row):
    # Normalize address to lowercase
    address = row['Address'].lower()

    # Check for direct street name match first (after converting to lowercase)
    street_match = df_gbd[df_gbd['Tên đường'].apply(lambda x: x in address)]

    if not street_match.empty:
        # If a match is found, get the corresponding district
        district = street_match.iloc[0]['District']

        # Now we need to check if the district is in Hồ Chí Minh
        if 'hồ chí minh' in address or 'hồ chí minh' in district.lower():
            return district_avg_prices.get(district, None)
        else:
            # If district is not in Hồ Chí Minh, exclude this row
            return None

    # If no direct match, check if the address contains district and "Hồ Chí Minh"
    for district in district_avg_prices:
        if contains_hcm_and_district(address, district):
            return district_avg_prices[district]

    # If no match is found or doesn't contain "Hồ Chí Minh", return None
    return None

# Apply the function to the property listing to assign district prices
df['District_Price'] = df.apply(assign_district_price, axis=1)

# Step 3: Filter out rows that don't match any Hồ Chí Minh district or do not contain Hồ Chí Minh
df_filtered = df[df['District_Price'].notna()]

# Save the cleaned DataFrame to a new CSV file
output_path = './cleaned_with_district_prices_filtered.csv'  # Replace with your desired output path
df_filtered.to_csv(output_path, index=False)

# Display the filtered DataFrame (for debugging purposes)
print(df_filtered.head())
