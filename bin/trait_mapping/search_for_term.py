#!/usr/bin/env python3

import argparse
from collections import defaultdict
from functools import lru_cache

import requests

base_url = 'https://www.ebi.ac.uk/ols4/api'
query_fields = ['label', 'synonym', 'description', 'short_form', 'obo_id', 'annotations', 'logical_description', 'iri']
field_list = ['iri', 'label', 'short_form', 'obo_id', 'ontology_name', 'ontology_prefix', 'description', 'type',
              'synonym', 'annotations', 'logical_description']

@lru_cache
def is_in_efo(iri):
    term_url = f'{base_url}/ontologies/efo/terms/{iri}'
    response = requests.get(term_url)
    if response.status_code == 200:
        return True
    else:
        return False

def format_mapping(result):
    if result.get('is_in_efo'):
        return f"{result['iri']}|{result['label']}|||EFO_CURRENT"
    else:
        return f"{result['iri']}|{result['label']}|||"

def format_outout(results_by_match_type):
    output = []
    if 'full_exact_match'  in results_by_match_type:
        output.append(format_mapping(results_by_match_type.get('full_exact_match')))
    else:
        output.append('')
    if 'contain_match'  in results_by_match_type:
        output.append(format_mapping(results_by_match_type.get('contain_match')))
    else:
        output.append('')
    for results in results_by_match_type.get('other_matches', []):
        output.append(format_mapping(results))
    return '\t'.join(output)

def add_fields_with_match(ontology_result, search_term):
    # Where was the match found ?
    contain_match_in = []
    full_exact_match_in = []
    for field in query_fields:
        if field in ontology_result:
            if isinstance(ontology_result[field], str):
                if  search_term.lower().strip() == ontology_result[field].lower().strip():
                    full_exact_match_in.append(field)
                elif search_term.lower() in ontology_result[field].lower():
                    contain_match_in.append(field)
            if isinstance(ontology_result[field], list):
                if [element for element in ontology_result[field] if search_term.lower().strip() == element.lower().strip()]:
                    full_exact_match_in.append(field)
                elif [element for element in ontology_result[field] if search_term.lower() in element.lower()]:
                    contain_match_in.append(field)

    ontology_result['contain_match'] = contain_match_in
    ontology_result['full_exact_match'] = full_exact_match_in
    # For the term not from EFO check if they are also in EFO
    if ontology_result.get('ontology_name') == 'efo':
        ontology_result['is_in_efo'] = True
    else:
        ontology_result['is_in_efo'] = is_in_efo(ontology_result.get('iri'))

def ontology_preference(result):
    if result.get('ontology_name') == 'efo':
        return 1
    elif result.get('is_in_efo'):
        return 2
    elif result.get('ontology_name') == 'mondo':
        return 3
    elif result.get('ontology_name') == 'hp':
        return 4
    else:
        return 5

def prioritise_ontology_search_results(ontology_results):
    tmp_results_by_match_type = defaultdict(list)
    for result in ontology_results:
        if result.get("full_exact_match"):
            tmp_results_by_match_type["full_exact_match"].append(result)
        elif result.get("contain_match"):
            tmp_results_by_match_type["contain_match"].append(result)
        else:
            tmp_results_by_match_type["other_match"].append(result)
    # only take the first full and contain match
    full_exact_match = next(iter(sorted(tmp_results_by_match_type["full_exact_match"], key=ontology_preference)), None)
    contain_match = next(iter(sorted(tmp_results_by_match_type["contain_match"], key=ontology_preference)), None)
    results_by_match_type = {}
    if full_exact_match:
        results_by_match_type["full_exact_match"] = full_exact_match
    if contain_match:
        results_by_match_type["contain_match"] = contain_match
    results_by_match_type["other_matches"] = sorted(tmp_results_by_match_type["other_match"], key=ontology_preference)
    return results_by_match_type

def search_ols4(term):
    search_url = base_url + "/search"
    params = {
        'q': term,
        'exact': 'true',
        'ontologies': 'efo,mondo,hp',
        'queryFileds': ','.join(query_fields),
        'fieldList': ','.join(field_list)
    }

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json()
        if results['response']['numFound'] > 0:
            search_results = []

            for result in results['response']['docs']:
                add_fields_with_match(result, term)
                search_results.append(result)
            results_by_match_type = prioritise_ontology_search_results(search_results)
            return format_outout(results_by_match_type)
        else:
            return ''

    except requests.RequestException as e:
        print(f"Error querying OLS4: {e}")
        return ''

def main():
    parser = argparse.ArgumentParser('Search OLS label for exact match')
    parser.add_argument('--search_file', type=str, help="path to a file containing the search terms. One per line")
    parser.add_argument('--output_file', type=str, help="path to the output file with the results. One per line")

    args = parser.parse_args()
    count = 0
    with open(args.search_file) as open_input, open(args.output_file, 'w') as open_output:
        for line in open_input:
            output = search_ols4(line.strip())
            open_output.write(f'{line.strip()}\t{output}\n')
            count += 1
            if count % 100 == 0:
                print(f'Processed {count} lines')


if __name__ == '__main__':
    main()

