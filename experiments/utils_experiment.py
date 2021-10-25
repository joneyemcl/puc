from collections import Counter
from fractions import Fraction
from quantulum3 import parser

from experiments.Constants import DATA_PATHS
from src.PUC import PUC
from src.utils import (
    read_dataset,
    convert_value,
    parse_cell_value,
)

import csv
import numpy as np
import pint
import sys
import time

sys.path.append("ccut/app/ccut_lib/")

# from main.canonical_compound_unit_transformation import CanonicalCompoundUnitTransformation as CCUT
# from qudt.ontology import UnitFactory
# from arpeggio import NoMatch

# from grobid_quantities.quantities import QuantitiesClient
from pathlib import Path

# from nltk.tag.stanford import StanfordNERTagger
# from nltk.tokenize import word_tokenize

# jar = "/Users/tceritli/Workspace/git/github/aida-repos/processing_meta_data/src/stanford-ner-2018-10-16/stanford-ner.jar"
# model = "/Users/tceritli/Workspace/git/github/aida-repos/processing_meta_data/src/stanford-ner-2018-10-16/data-dictionary.ser.gz"
# trained_ner_tagger = StanfordNERTagger(model, jar, encoding="utf8")

Q_ = pint.UnitRegistry().Quantity
# ccut = CCUT()
#
# grobid_server_url = "http://localhost:8060/service"
# client = QuantitiesClient(apiBase=grobid_server_url)

# unitCanonicalizer = UnitCanonicalizer(unit_ontology_path='notebooks/unit-normalization/units_wikidata.json')
unitCanonicalizer = PUC(unit_ontology_path="experiments/inputs/unit_ontology.json")


def quantulum_predict(_cell_value):
    quants = parser.parse(_cell_value)
    if len(quants) > 1:
        print("more than one quant!", quants)

    if len(quants) == 0:
        return "Not Identified"
    else:
        prediction = {
            "magnitude": quants[0].value,
            "unit": quants[0].unit.name,
            "entity": quants[0].unit.entity.name,
        }
    return prediction


def pint_predict(_cell_value):
    quants = Q_(_cell_value)
    temp = list(quants.dimensionality.keys())
    if len(temp) > 0:
        entity = list(quants.dimensionality.keys())[0].replace("[", "").replace("]", "")
    else:
        entity = "unknown"
    prediction = {
        "magnitude": quants.magnitude,
        "unit": str(quants.units),
        "entity": entity,
    }
    return prediction


def ner_predict(unit):

    # unit = parse_cell_value(_cell_value)[1]
    # print('unit=', unit)
    t = trained_ner_tagger.tag((unit,))[0][1]
    # print('t=', t)
    if unit == "":
        return "dimensionless"
    else:
        return t


def grobid_quantities_predict(_cell_value):
    res = client.process_text(_cell_value)
    if res[0] == 200 and "measurements" in res[1]:

        res = res[1]["measurements"][0]
        if "quantity" in res:
            keyword = "quantity"
        elif "quantityMost" in res:
            keyword = "quantityMost"
        elif "quantityLeast" in res:
            keyword = "quantityLeast"
        elif "quantities" in res:
            keyword = "quantities"

        if keyword == "quantities":
            raw_magnitude = float(res[keyword][0]["rawValue"])
        else:
            raw_magnitude = float(res[keyword]["rawValue"])

        if "rawUnit" in res[keyword]:
            raw_unit = res[keyword]["rawUnit"]["name"]
            raw_unit_name = raw_unit
            if "type" in res[keyword]:
                measurement_type = res[keyword]["type"]
            else:
                measurement_type = "unknown"

            # # get name from symbol
            # raw_unit_name = [rawUnit, measurement_type]
        else:
            raw_unit_name = "Not Identified"
            measurement_type = "unknown"

        prediction = {
            "magnitude": raw_magnitude,
            "unit": raw_unit_name,
            "entity": measurement_type,
        }
    else:
        prediction = "Not Identified"

    return prediction


# def unit_canonicalizer_predict(_cell_value, _cell_type, exponential=False):
#     if exponential:
#         print('based on exponential!')
#         [y, output] = unitCanonicalizer.identify_unit_cell_exponential(_cell_value, _cell_type)
#     else:
#         [y, output] = unitCanonicalizer.identify_unit_cell(_cell_value, _cell_type)
#     # fix annotations for 'magnitude-less'
#     if y == '':
#         y = 1.0
#     prediction = {'magnitude':y, 'unit':output}
#
#     return prediction


def unit_canonicalizer_predict(y_i, t, u):
    print("y_i, t, u", y_i, len(y_i), t, u)
    v_i, z_i = unitCanonicalizer.infer_cell_unit(y_i, t, u)
    prediction = {"magnitude": v_i, "unit": z_i}
    return z_i


# def ccut_predict(_cell_value):
#     canonical_form = ccut.ccu_repr(_cell_value)
#
#     magnitude = canonical_form['ccut:hasPart'][0]['ccut:multiplier']
#     unit = canonical_form['ccut:hasPart'][0]['qudtp:symbol']
#     if unit == 'UNKNOWN TYPE':
#         prediction = 'UNKNOWN TYPE'
#     else:
#         if 'ccut:prefix' in canonical_form['ccut:hasPart'][0]:
#             unit = canonical_form['ccut:hasPart'][0]['ccut:prefix'].split('#')[-1] + canonical_form['ccut:hasPart'][0]['qudtp:quantityKind'].split('#')[-1]
#         else:
#             unit = canonical_form['ccut:hasPart'][0]['qudtp:quantityKind'].split('#')[-1]
#         prediction = {'magnitude':magnitude, 'unit':unit.lower()}
#     return prediction


def ccut_predict(_cell_value):
    canonical_form = ccut.ccu_repr(_cell_value)

    magnitude = canonical_form["ccut:hasPart"][0]["ccut:multiplier"]
    unit = canonical_form["ccut:hasPart"][0]["qudtp:symbol"]

    if unit == "UNKNOWN TYPE":
        prediction = "UNKNOWN TYPE"
    else:
        if "ccut:prefix" in canonical_form["ccut:hasPart"][0]:
            unit = (
                canonical_form["ccut:hasPart"][0]["ccut:prefix"].split("#")[-1]
                + canonical_form["ccut:hasPart"][0]["qudtp:quantityKind"].split("#")[-1]
            )
        else:
            unit = canonical_form["ccut:hasPart"][0]["qudtp:quantityKind"].split("#")[
                -1
            ]

        if unit != "UNKNOWN TYPE":
            qudt_unit = UnitFactory.get_unit("http://qudt.org/vocab/unit#" + unit)
            temp = qudt_unit.type_uri.split("#")
            if len(temp) > 1:
                entity = qudt_unit.type_uri.split("#")[1].replace("Unit", "").lower()
            else:
                entity = "unknown"
        else:
            entity = "unknown"

        prediction = {"magnitude": magnitude, "unit": unit.lower(), "entity": entity}

    return prediction


def evaluate_prediction(truth, prediction):
    # to convert '1/2' to 0.5
    if (type(prediction) == dict) and type(prediction["magnitude"]) == str:

        if prediction["magnitude"] == "":
            prediction[
                "magnitude"
            ] = 1.0  # missing magnitude and filling it as 1 are assumed to be both correct.
        else:
            prediction["magnitude"] = float(Fraction(prediction["magnitude"]))

    if (type(prediction) == dict) and type(prediction["unit"]) == list:
        if len(prediction["unit"]) == 1:
            if type(truth["unit"]) == list:
                return (
                    (type(prediction) == dict)
                    and (truth["magnitude"] == float(prediction["magnitude"]))
                    and (
                        len(set(prediction["unit"]).intersection(set(truth["unit"])))
                        > 0
                    )
                )
            else:
                return (
                    (type(prediction) == dict)
                    and (truth["magnitude"] == float(prediction["magnitude"]))
                    and (truth["unit"] in prediction["unit"][0])
                )
        else:
            if len(prediction["unit"]) > 1:
                print("multiple matches", prediction["unit"])
            return False

    else:
        return (
            (type(prediction) == dict)
            and (truth["magnitude"] == float(prediction["magnitude"]))
            and (prediction["unit"] in truth["unit"])
        )
    # print(truth, prediction, (type(prediction) == dict) and (truth['magnitude'] == float(prediction['magnitude'])) and (prediction['unit'] in truth['unit']))


def evaluate_identification_experiment(dataset, columns, annotations, ps):
    evaluations = {}
    df = read_dataset(dataset, ALL_PATHS=DATA_PATHS)

    for column in columns:
        correct = 0
        false = 0
        unique_vals = np.unique(df[column].values)
        evaluations[column] = {}
        predictions = ps[column]

        for unique_value in unique_vals:
            if unique_value in annotations:
                if predictions == "no unit":
                    false += 1
                elif evaluate_prediction(
                    annotations[unique_value], predictions[unique_value]
                ):
                    correct += 1
                else:
                    print(
                        "False prediction!:",
                        unique_value,
                        annotations[unique_value],
                        predictions[unique_value],
                    )
                    false += 1
            else:
                print("Not annotated!", unique_value, len(unique_value))

        evaluations[column]["correct"] = correct
        evaluations[column]["false"] = false

    return evaluations


def evaluate_euc_prediction(truth, prediction, column_unit_symbol):

    # to convert '1/2' to 0.5
    if (type(prediction) == dict) and type(prediction["magnitude"]) == str:
        prediction["magnitude"] = float(Fraction(prediction["magnitude"]))

    float_magnitude = float(prediction["magnitude"])
    if type(prediction) != dict:
        print("prediction is not a dictionary!!!!")
        return None
    else:
        if type(prediction["unit"]) == list:
            if len(prediction["unit"]) == 1:

                if type(truth["unit"]) == list:
                    # when they are both lists
                    intersection = set(prediction["unit"]).intersection(
                        set(truth["unit"])
                    )
                    identification = (truth["magnitude"] == float_magnitude) and (
                        len(intersection) > 0
                    )
                    conversion_predicted = convert_value(
                        float_magnitude, list(intersection)[0], column_unit_symbol
                    )
                    conversion_truth = convert_value(
                        truth["magnitude"], list(intersection)[0], column_unit_symbol
                    )
                    return identification and (conversion_predicted == conversion_truth)
                else:
                    # when only the prediction is a list
                    identification = (truth["magnitude"] == float_magnitude) and (
                        truth["unit"] in prediction["unit"]
                    )
                    conversion_predicted = convert_value(
                        float_magnitude, prediction["unit"][0], column_unit_symbol
                    )
                    conversion_truth = convert_value(
                        truth["magnitude"], truth["unit"], column_unit_symbol
                    )
                    return identification and (conversion_predicted == conversion_truth)
            else:
                if len(prediction["unit"]) > 1:
                    print("multiple matches", prediction["unit"])
                return None

        else:
            # when prediction is not a list
            identification = (truth["magnitude"] == float_magnitude) and (
                prediction["unit"] in truth["unit"]
            )
            conversion_predicted = convert_value(
                float_magnitude, prediction["unit"], column_unit_symbol
            )
            conversion_truth = convert_value(
                truth["magnitude"], prediction["unit"], column_unit_symbol
            )

            return identification and (conversion_predicted == conversion_truth)


def evaluate_euc_experiment(df, annotations, predictions, column_unit):

    evaluations = {}
    pint_dimerrors = []
    false_predictions = []

    correct = 0
    unique_values = np.unique(df.values)
    for unique_value in unique_values:
        if unique_value in annotations:
            # print('\tunique_value', unique_value)
            # print('\tcolumn_unit_symbol', column_unit_symbol)
            # print('\tannotation', annotations[unique_value])
            # print('\tprediction', predictions[unique_value])

            try:
                res = evaluate_euc_prediction(
                    annotations[unique_value], predictions[unique_value], column_unit
                )
            except DimensionalityError:
                res = "DimensionalityError"
                pint_dimerrors.append(unique_value)
            if res:
                correct += 1
            else:
                false_predictions.append(unique_value)
                # print('False prediction!:', unique_value, annotations[unique_value], predictions[unique_value], column_unit_symbol)
        else:
            print("Not annotated!:", unique_value, predictions[unique_value])

    evaluations["correct"] = correct
    evaluations["pint_dimerrors"] = pint_dimerrors
    evaluations["false_predictions"] = false_predictions
    return evaluations


def evaluate_type_experiment(dataset, columns, annotations, predictions, features):
    evaluations = {}

    for column in columns:
        evaluations[column] = {
            feature: {
                "correct": annotations[column],
                "predict": predictions[column][feature],
            }
            for feature in features
        }

    return evaluations


def evaluate_column_measurement_type_experiment(columns, annotations, predictions):
    evaluations = {}

    for column in columns:
        evaluations[column] = {
            "correct": annotations[column],
            "predict": predictions[column],
        }

    return evaluations


def save_output(dataset_name, predicted_types):
    with open("experiments/outputs/" + dataset_name + ".csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Column", "ptype"])
        for column_name in predicted_types:
            writer.writerow([column_name, predicted_types[column_name]])


def infer_type_column(df, _column_name, _features):

    x = df[_column_name].to_frame()[_column_name].values

    t = {}
    p_z = {}
    for _feature in _features:
        t[_feature], p_z[_feature] = unitCanonicalizer.infer_column_unit_type(
            x, _column_name, _feature
        )

    return t, p_z


def parse_values(y):
    z = [parse_cell_value(y_i) for y_i in y]
    v = [z_i[0] for z_i in z]
    x = [z_i[1] for z_i in z]
    return z, v, x


def generate_likelihoods(x):
    unitCanonicalizer.generate_likelihoods(x)


def infer_column_dimension():
    return unitCanonicalizer.infer_column_dimension()


def infer_column_unit(u):
    return unitCanonicalizer.infer_column_unit(u)


def convert_row_unit(v_i, u_i, u):
    return unitCanonicalizer.convert_row_unit(v_i, u_i, u)


def infer_cell_units(y, v, x, z, k):
    return unitCanonicalizer.infer_cell_units(y, v, x, z, k)


def infer_cell_dimensions(y, v, x, k):
    return unitCanonicalizer.infer_cell_dimensions(y, v, x, k)


def infer_column_unit(u):

    unit_symbol_predicted = unitCanonicalizer.infer_column_unit(u)

    return unit_symbol_predicted


def identify_unit_cell(y_i, method, t=None):
    if method == "pint":
        prediction = pint_predict(y_i)
    elif method == "quantulum":
        prediction = quantulum_predict(y_i)
    elif method == "ccut":
        prediction = ccut_predict(y_i)
    elif method == "grobid_quantities":
        prediction = grobid_quantities_predict(y_i)
    elif method == "unit_canonicalizer":
        prediction = unit_canonicalizer_predict(y_i, t)
    else:
        return "unknown method!"

    return prediction


def identify_row_unit(x_i, method, t=None, u=None):
    if method == "pint":
        prediction = pint_predict(x_i)
    elif method == "quantulum":
        prediction = quantulum_predict(x_i)
    elif method == "ccut":
        prediction = ccut_predict(x_i)
    elif method == "grobid_quantities":
        prediction = grobid_quantities_predict(x_i)
    elif method == "unit_canonicalizer":
        prediction = unit_canonicalizer_predict(x_i, t, u)
    else:
        return "unknown method!"

    return prediction


def run_type_experiment(df, columns, features):

    predicted_types = {}
    p_z = {}
    if columns == "all":
        columns = df.columns

    for column in columns:
        predicted_types[column], p_z[column] = infer_type_column(df, column, features)

    # save_output(dataset, predicted_types)
    return predicted_types, p_z


def run_measurement_type_experiment(df, columns):

    predicted_types = {}
    if columns == "all":
        columns = df.columns

    for column in columns:
        predicted_types[column] = infer_column_dimension(df, column)

    # save_output(dataset, predicted_types)
    return predicted_types


def run_dimension_experiments(df, columns):
    predicted_col_dims = {}
    predicted_cell_units = {}
    predicted_cell_dims = {}
    if columns == "all":
        columns = df.columns

    times = {}
    for column in columns:
        # why? this doesn't feel correct. but it's useful for fast computation.
        # it's actually fixed in the other evaluations
        y = np.unique(df[column].to_frame()[column].values)
        _, v, x = parse_values(y)

        # # for unique symbols
        # x = np.unique(x)

        t0 = time.time()
        generate_likelihoods(x)
        t = infer_column_dimension()
        delta_t = time.time() - t0
        times[column] = delta_t

        if t == "no unit":
            z = "no unit"
            u = "no unit"
        else:
            z = infer_cell_dimensions(y, v, x, t)
            u = infer_cell_units(y, v, x, z, t)

        predicted_col_dims[column] = t
        predicted_cell_units[column] = u
        predicted_cell_dims[column] = z

    return predicted_col_dims, predicted_cell_units, times


def run_competitor_column_experiments(df, columns, method):
    if method == "Quantulum":
        return run_quantulum_column_experiments(df, columns)
    elif method == "ccut":
        return run_ccut_column_experiments(df, columns)
    elif method == "grobid":
        return run_grobid_column_experiments(df, columns)
    elif method == "Pint":
        return run_pint_column_experiments(df, columns)
    elif method == "ner":
        return run_ner_column_experiments(df, columns)


def run_quantulum_column_experiments(df, columns):

    predicted_dims = {}
    if columns == "all":
        columns = df.columns
    times = {}
    not_detected = []
    for column in columns:
        temp_dims = []
        unique_values = df[column].unique()
        t0 = time.time()
        for unique_value in unique_values:
            try:
                predicted_dim = quantulum_predict(unique_value)["entity"]
                temp_dims.append(predicted_dim)
            except:
                not_detected.append(unique_value)

        cntr = Counter(temp_dims)
        if len(cntr) == 0:
            t = "unknown"
        else:
            t = cntr.most_common(1)[0][0]
            if t == "dimensionless":
                t = cntr.most_common(2)[1][0]

        delta_t = time.time() - t0
        predicted_dims[column] = t
        times[column] = delta_t

    return predicted_dims, None, times


def run_ccut_column_experiments(df, columns):

    predicted_types = {}
    if columns == "all":
        columns = df.columns
    times = {}
    for column in columns:
        temp_types = []
        unique_values = df[column].unique()
        t0 = time.time()
        for unique_value in unique_values:
            try:
                predicted_type = ccut_predict(unique_value)["entity"]
                temp_types.append(predicted_type)
            except:
                print(unique_value, " is not detected")

        cntr = Counter(temp_types)
        if len(cntr) == 0:
            t = "unknown"
        else:
            t = cntr.most_common(1)[0][0]
            if t == "dimensionless":
                t = cntr.most_common(2)[1][0]

        delta_t = time.time() - t0
        predicted_types[column] = t
        times[column] = delta_t

    return predicted_types, times


def run_grobid_column_experiments(df, columns):

    predicted_types = {}
    if columns == "all":
        columns = df.columns
    times = {}
    for column in columns:
        temp_types = []
        unique_values = df[column].unique()
        t0 = time.time()
        for unique_value in unique_values:
            try:
                predicted_type = grobid_quantities_predict(unique_value)["entity"]
                temp_types.append(predicted_type)
            except:
                print(unique_value, " is not detected")

        cntr = Counter(temp_types)
        if len(cntr) == 0:
            t = "unknown"
        else:
            t = cntr.most_common(1)[0][0]
            if t == "dimensionless":
                t = cntr.most_common(2)[1][0]

        delta_t = time.time() - t0
        predicted_types[column] = t
        times[column] = delta_t

    return predicted_types, times


def run_pint_column_experiments(df, columns):
    predicted_dims = {}
    if columns == "all":
        columns = df.columns
    times = {}
    not_detected = []
    for column in columns:
        temp_dims = []
        unique_values = df[column].unique()
        t0 = time.time()
        for unique_value in unique_values:
            try:
                predicted_dim = pint_predict(unique_value)["entity"]
                temp_dims.append(predicted_dim)
            except:
                not_detected.append(unique_value)

        cntr = Counter(temp_dims)
        if len(cntr) == 0:
            t = "unknown"
        else:
            t = cntr.most_common(1)[0][0]
            if t == "dimensionless":
                t = cntr.most_common(2)[1][0]

        delta_t = time.time() - t0
        predicted_dims[column] = t
        times[column] = delta_t

    return predicted_dims, None, times


def run_ner_column_experiments(df, columns):

    predicted_types = {}
    if columns == "all":
        columns = df.columns

    times = {}
    for column in columns:
        type_counts = {}
        unique_values = df[column].unique()
        t0 = time.time()
        units = [parse_cell_value(unique_value)[1] for unique_value in unique_values]
        unit_counts = Counter(units)

        for unique_unit in np.unique(units):
            print("processing=", unique_unit)
            try:
                predicted_type = ner_predict(unique_unit)
                if predicted_type in type_counts:
                    type_counts[predicted_type] += unit_counts[unique_unit]
                else:
                    type_counts[predicted_type] = unit_counts[unique_unit]

                print("unique_unit=", unique_unit)
                print("predicted_type=", predicted_type)
            except:
                print(unique_unit, " is not detected")

        if len(type_counts) == 0:
            t = "unknown"
        else:
            t = max(type_counts, key=type_counts.get)
            if t == "dimensionless":
                t = list(sorted(type_counts.values()))[-2]

        delta_t = time.time() - t0
        predicted_types[column] = t
        times[column] = delta_t

    return predicted_types, times


def run_identification_experiment(
    df, columns, method, cell_type=None, features=None, exp=False
):
    predicted_units = {}

    if method == "unit_canonicalizer":
        print(method)
        for column in columns:
            print("column", column)
            unique_vals = np.unique(df[column].values)
            for cell_value in unique_vals:
                res = identify_unit_cell(
                    cell_value,
                    method,
                    cell_type=cell_type[column][features[0]],
                    exp=exp,
                )
                print("unit_canonicalizer", cell_value, cell_type[column], res)
                predicted_units[cell_value] = res
    else:
        unique_vals = np.unique(df[columns].values)

        for cell_value in unique_vals:
            try:
                res = identify_unit_cell(cell_value, method)
            except UndefinedUnitError:
                res = "UndefinedUnitError"
            except ValueError:
                res = "ValueError"
            except FileNotFoundError:
                res = "FileNotFoundError"
            except AttributeError:
                res = "AttributeError"
            except TokenError:
                res = "TokenError"
            except TypeError:
                res = "TypeError"
            except KeyError:
                res = "KeyError"
            except NoMatch:
                res = "NoMatch"

            predicted_units[cell_value] = res

    return predicted_units


def run_row_unit_experiment(df, columns, method, t=None, u=None):
    predicted_row_units = {}
    for column in columns:
        predicted_column_row_units = {}
        unique_vals = np.unique(df[column].values)
        for cell_value in unique_vals:
            try:
                res = identify_unit_cell(cell_value, method)
            except UndefinedUnitError:
                res = "UndefinedUnitError"
            except ValueError:
                res = "ValueError"
            except FileNotFoundError:
                res = "FileNotFoundError"
            except AttributeError:
                res = "AttributeError"
            except TokenError:
                res = "TokenError"
            except TypeError:
                res = "TypeError"
            except KeyError:
                res = "KeyError"
            except NoMatch:
                res = "NoMatch"

            predicted_column_row_units[cell_value] = res

        predicted_row_units[column] = predicted_column_row_units

    return predicted_row_units


def run_identification_cell_value(cell_value, method, cell_type=None):

    if method == "unit_canonicalizer":
        res = identify_unit_cell(cell_value, method, cell_type)
    else:
        try:
            res = identify_unit_cell(cell_value, method)
        except UndefinedUnitError:
            res = "UndefinedUnitError"
        except ValueError:
            res = "ValueError"
        except FileNotFoundError:
            res = "FileNotFoundError"
        except AttributeError:
            res = "AttributeError"
        except TokenError:
            res = "TokenError"
        except TypeError:
            res = "TypeError"
        except KeyError:
            res = "KeyError"
        except NoMatch:
            res = "NoMatch"

    return res
