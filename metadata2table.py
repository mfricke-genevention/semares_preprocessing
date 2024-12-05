import json
import pandas as pd
import csv
import argparse
import sys
import os


def option_parser():
    parser = argparse.ArgumentParser(description="metadata2table")
    parser.add_argument('--metadata', "-m",
                        help='metadata json file', dest="metadata")
    parser.add_argument('--config', "-c",
                        help='table configuration file', dest="config")
    parser.add_argument('--pathes', "-p",
                        help='original pathes to select meta data objects', dest="pathes")
    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit("Missing parameters!")

    return args


def get(mixed_obejct, keys, default=None):
    """safely get result from (nested) dict or array

    Args:
        mixed_obejct (TYPE): mixed obejct e.g {"a": {"b": [1, 2, {"c": 1}]}}
        keys (TYPE): key or list of keys
        default (None, optional): default to return on fail

    Returns:
        TYPE: result based on key
    """
    result = mixed_obejct
    if not isinstance(keys, list):
        keys = [keys]
    try:
        for key in keys:
            try:
                result = result[key]
            except KeyError:
                if isinstance(key, int) and isinstance(result, dict):
                    result = list(result.values())[key]
                else:
                    raise KeyError
        return result
    except KeyError:
        return default
    except IndexError:
        return default


def set_timepoint_index(field, item):
    if "$TIMEPOINT" in field:
        timepoint = get(
            item, ["sample", "associations", 0, "timepoint"])
        timepoint_index = None
        if timepoint:
            timepoints = get(item, ["individual", "timepoints"])
            if timepoints is not None:
                for i, timepoint_content in enumerate(timepoints):
                    if (timepoint_content.get("timepoint_code") == timepoint or
                        timepoint_content.get("timepoint_name") == timepoint or
                            timepoint_content.get("timepoint_termId") == timepoint):
                        field[field.index("$TIMEPOINT")] = i
                        timepoint_index = i
                        break
            else:
                raise ValueError(
                    "No timepoints found. Check if the workflow as 'Include Clinical Metadata' enabled.")

        if timepoint is None:
            raise ValueError(f"No timepoint specified in metadata")
        if timepoint_index is None:
            raise ValueError(f"Timepoint '{timepoint}' can't be resolved!")


def read_json_file(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))


def transform_metadata(table_config, metadata, file_pathes):
    metadata_list = []
    column_config = table_config.get("columns")

    for metadata_item in metadata:
        item = list(metadata_item.values())[0]
        key = list(metadata_item.keys())[0]
        if key in file_pathes:
            metadata_map = {}
            for config in column_config:
                field = config.get("field")
                default = config.get("default")
                object_type = config.get("object_type")
                header_name = config.get("header_name")
                key_list = [object_type] + field
                set_timepoint_index(key_list, item)
                value = get(item, key_list)
                if value is None and default is not None:
                    value = default

                metadata_map[header_name] = value
            metadata_list.append(metadata_map)
    table = pd.DataFrame.from_records(metadata_list)
    write_table(table, table_config)


def write_table(table, table_config):
    quotechar = table_config.get("quotechar", "\"")
    quoting = csv.QUOTE_NONE
    if quotechar:
        quoting = csv.QUOTE_MINIMAL
    output_dir = table_config.get("output", "./")
    if output_dir != "./":
        os.makedirs(output_dir, exist_ok=True)
    table.to_csv(
        table_config.get("output", "./") +
        table_config.get("file_name", "metadata.csv"),
        sep=table_config.get("sep"),
        quotechar=quotechar, quoting=quoting, index=False)


def main():
    args = option_parser()
    table_config = read_json_file(args.config)
    metadata = read_json_file(args.metadata)
    transform_metadata(table_config, metadata, args.pathes)


if __name__ == "__main__":
    main()
