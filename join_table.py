import pandas as pd
import json
import argparse
import sys
import csv
import os


def get(mixed_object, keys, default=None):
    """safely get result from (nested) dict or array

    Args:
        mixed_obejct (TYPE): mixed obejct e.g {"a": {"b": [1, 2, {"c": 1}]}}
        keys (TYPE): key or list of keys
        default (None, optional): default to return on fail

    Returns:
        TYPE: result based on key
    """
    result = mixed_object
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


def option_parser():
    parser = argparse.ArgumentParser(description="metadata2table")
    parser.add_argument('--metadata', "-m",
                        help='metadata json file', dest="metadata")
    parser.add_argument('--config', "-c",
                        help='table configuration file', dest="config")
    parser.add_argument('--files', "-f",
                        help='files to join', dest="files", nargs='+')
    parser.add_argument('--pathes', "-p",
                        help='original pathes', dest="pathes")
    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit("Missing parameters!")

    return args


def read_json_file(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))


def check_column_exists(columns, table):
    i = 0
    result_column = None
    for column in columns:
        if column in table:
            result_column = column
            i += 1

    if i == 0:
        raise ValueError("Column not found!")
    if i > 1:
        raise ValueError("Column is not unique!")

    return result_column


def find_metadata(metadata, path):
    metadata_match = {}
    for matching_metadata in metadata:
        dataset_pathes = matching_metadata.keys()
        for dataset_path in dataset_pathes:
            tmp = dataset_path.split("data/")
            dataset_id = tmp[-1]
            if dataset_id in path:
                metadata_match = matching_metadata[dataset_path]
    if not metadata_match:
        raise ValueError(f"Can't find metadata for file: {path}")
    return metadata_match


def get_quoting(quotechar):
    quoting = csv.QUOTE_NONE
    if quotechar:
        quoting = csv.QUOTE_MINIMAL
    return quoting


def get_new_column_name(content_config, metadata_match):
    name_pattern = content_config.get("name")
    name_maps = content_config.get("maps")
    name_map = {}
    for map in name_maps:
        key = map.get("name")
        fields = map.get("field")
        object_type = map.get("object_type")
        key_list = [object_type] + fields
        name_map[key] = get(metadata_match, key_list)
    new_column_name = name_pattern.format(**name_map)
    return new_column_name


def read_csv_table(file, table_config):
    quotechar = table_config.get("quotechar")
    quoting = get_quoting(quotechar)
    table = pd.read_csv(file, sep=table_config.get(
        "sep"), quoting=quoting, quotechar=quotechar)
    return table


def write_csv_table(table, table_config):
    table_config_output = table_config.get("output")
    quotechar = table_config_output.get("quotechar")
    quoting = get_quoting(quotechar)
    os.makedirs(table_config_output.get("path", "./"), exist_ok=True)
    table.to_csv(
        table_config_output.get("path", "./") +
        table_config_output.get("file_name", "matrix.csv"),
        sep=table_config_output.get("sep"),
        quotechar=quotechar, quoting=quoting, index=False)


def transform_table(table, metadata_match, table_config):
    join_config = table_config.get("join")
    content_columns = table_config.get("columns")
    join_column = check_column_exists(join_config.get("columns"), table)
    join_column_name = join_config.get("name")
    column_selection = [join_column]
    rename_columns = [join_column_name]

    for content_config in content_columns:
        column_names = content_config.get("input")
        content_column = check_column_exists(column_names, table)
        new_column_name = get_new_column_name(content_config, metadata_match)
        column_selection.append(content_column)
        rename_columns.append(new_column_name)

    table_selection = table[column_selection]
    table_selection.columns = rename_columns

    return table_selection


def join_table(file_path, table_config, metadata):
    result_matrix = None
    input_config = table_config.get("input")
    join_column_name = input_config.get("name")

    for file, path in file_path:
        input_table = read_csv_table(file, input_config)
        metadata_match = find_metadata(metadata, path)
        table_selection = transform_table(
            input_table, metadata_match, table_config)

        if result_matrix is None:
            result_matrix = table_selection
        else:
            result_matrix = pd.merge(
                result_matrix, table_selection,
                on=join_column_name, how="outer")

    if result_matrix is not None:
        write_csv_table(result_matrix, table_config)


def main():
    args = option_parser()
    metadata = read_json_file(args.metadata)
    table_config = read_json_file(args.config)
    pathes = args.pathes.split(",")
    files = args.files
    file_path = zip(files, pathes)
    join_table(file_path, table_config, metadata)


if __name__ == "__main__":
    main()
