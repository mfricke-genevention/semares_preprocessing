import json
# file_name = "gene_expression"
# data_type = "transcriptomics"
file_name = "protein_abundance"
data_type = "proteomics"

input_json = json.load(open(f"./metadata_{data_type}.json"))
new_json = []
files = []
for items in input_json:
    for key, value in items.items():
        new_key = value.get("sample", {}).get("name")
        day = new_key.split("_")[-1]
        new_key = f"./examples/{data_type}/{new_key}/{file_name}_{day}.csv"
        if day == "50":
            files.append(new_key)
        new_json.append(
            {
                new_key: value
            }
        )
json.dump(new_json, open(f"./metadata_{data_type}_adjusted.json","w"))

print(",".join(files))