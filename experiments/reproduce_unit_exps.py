def run(data_paths, datasets, methods):
    cell_predictions = {dataset: {} for dataset in datasets}
    dim_predictions = {dataset: {} for dataset in datasets}
    for dataset in datasets:
        print("running on " + dataset + "...")

        df = read_dataset(dataset, ALL_PATHS=DATA_PATHS)
        cols = data_paths[dataset]["columns"]

        for method in methods:
            if method == "PUC":
                (
                    dim_prediction,
                    cell_types,
                    unit_prediction,
                    _,
                ) = run_dimension_experiments(df, cols)
                dim_predictions[dataset][method] = dim_prediction
                cell_predictions[dataset][method] = unit_prediction
            else:
                cell_prediction = run_identification_experiment(
                    df, cols, method, None, None
                )
                cell_predictions[dataset][method] = cell_prediction

    return cell_predictions


def eval_predictions(data_paths, datasets, input_path, predictions, methods):
    # Load cell annotations
    annotations = np.load(input_path + "updated_cell_annotations1554.npy", allow_pickle=True).item()
    evaluations = {}
    
    for dataset in datasets:
        # Initialize evaluations for the dataset
        columns = data_paths[dataset]["columns"]
        evaluations[dataset] = {col: {method: {"correct": 0, "false": 0} for method in methods} for col in columns}
        
        # Check if the dataset exists in annotations
        if dataset not in annotations:
            print(f"Warning: No annotations found for dataset '{dataset}'. Skipping evaluation.")
            continue
        
        # Perform evaluation if annotations are available
        for method in methods:
            if dataset in predictions and method in predictions[dataset]:  # Ensure the method exists in predictions
                results = evaluate_identification_experiment(
                    dataset,
                    columns,
                    method,
                    annotations[dataset],
                    predictions[dataset][method],
                )
                for col in results:
                    evaluations[dataset][col][method] = results[col]
            else:
                print(f"Warning: No predictions found for method '{method}' in dataset '{dataset}'.")
    
    return evaluations


def report_results(predictions, evaluations, output_path):
    # save predictions
    np_save(output_path, "unit_predictions.npy", predictions)
    np_save(output_path, "unit_evaluations.npy", evaluations)

    # Calculate the results and putting them in a dataframe
    evaluations_df = as_table_cell(evaluations, methods)

    # Save the performance
    metrics_df = calculate_metrics_cells(evaluations_df, methods)
    metrics_df.T.to_latex(output_path + "unit_evaluations.tex")


def main(data_paths, datasets, methods, input_path, output_path):
    predictions = run(data_paths, datasets, methods)
    evaluations = eval_predictions(data_paths, datasets, input_path, predictions, methods)
    report_results(predictions, evaluations, output_path)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, "../src/")

    from experiments.Constants import DATA_PATHS, DATASETS, INPUT_ROOT, OUTPUT_ROOT
    from experiments.utils_experiment import (
        run_dimension_experiments,
        run_identification_experiment,
    )
    from experiments.utils_IO import np_save, read_dataset
    from experiments.utils_evals import (
        as_table_cell,
        calculate_metrics_cells,
        evaluate_identification_experiment,
    )

    import numpy as np

    methods = ["Pint", "Quantulum", "PUC"]
    # use the following if the other competitor methods are setup
    # methods = ["CCUT", "GQ", "Pint", "Quantulum", "PUC"]
    main(DATA_PATHS, DATASETS, methods, INPUT_ROOT, OUTPUT_ROOT)
