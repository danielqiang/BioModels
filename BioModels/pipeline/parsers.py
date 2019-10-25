from typing import TextIO, Collection
from bs4 import BeautifulSoup
from os.path import basename

__all__ = ['parse_derived_model', 'parse_mcmp_model', 'parse_species_data', 'get_all_go_compartments']


def parse_mcmp_model(sbml_file: TextIO, all_go_compartments: Collection, skip_single_cmp_models=True):
    """
    Extracts all compartments from an SBML file and returns a generator of
    (Model, Edge, Parent Model) 3-tuples each representing a relationship
    between an SBML model and one of its defined compartments.

    :param sbml_file: SBML file handle.
    :param all_go_compartments: Collection of all known GO compartment names.
                            Acts as a preprocessed data reference for the
                            parser; can be obtained by calling
                            get_all_go_compartments().
    :param skip_single_cmp_models: If True, does not parse 'file' if it
                            is a single compartment model.
    :rtype: generator
    """
    soup = BeautifulSoup(sbml_file, features='lxml')
    compartment_tags = soup.find_all("compartment")

    if len(compartment_tags) < 2 and skip_single_cmp_models:
        return

    model_name = str(basename(sbml_file.name).split('.')[0])
    model_provider = 'biomodels.db'
    model_URI = 'http://identifiers.org/biomodels.db/' + model_name
    model_publication_date = _extract_publication_date(soup)

    for compartment_tag in compartment_tags:
        compartment_data = {
            'name': _get_name(compartment_tag, all_go_compartments).lower(),
            # Color compartments yellow
            'color': 'yellow',
        }
        model_data = {
            'name': model_name,
            'provider': model_provider,
            'URI': model_URI,
            'created': model_publication_date,
            # Color BioModels green
            'color': 'green'
        }

        go_id = _get_go_id(compartment_tag)
        if go_id:
            compartment_data['identifier'] = go_id

        yield model_data, 'isPartOf', compartment_data


def _get_go_id(compartment_tag: BeautifulSoup):
    """
    Extracts and returns the GO id annotation from a compartment tag.
    If no GO id annotation exists, return None.

    :param compartment_tag: BeautifulSoup Tag for a single compartment
                            in a multi-compartment model.
    """
    try:
        go_id = compartment_tag.find("rdf:li")['rdf:resource'].split('/')[-1]
        return go_id
    # No annotation containing the GO id exists for the SBML compartment tag.
    except TypeError:
        return None


def _get_name(compartment_tag: BeautifulSoup, all_go_compartments):
    """
    Extracts and returns the compartment name from a compartment tag.

    Uses the GO id annotation if it exists; if not, attempts to
    find a close GO compartment name match. If no satisfactory
    match is found, use the tag's name/id attribute instead.

    :param compartment_tag: BeautifulSoup Tag for a single compartment
                            in a multi-compartment model.
    :param all_go_compartments: Collection of all known GO compartment names.
                            Acts as a preprocessed data reference for the
                            parser; can be obtained by calling
                            get_all_go_compartments()
    :rtype: str
    """
    from BioModels.tools import get_go_json
    from difflib import get_close_matches

    try:
        # Try to extract the Gene Ontology id (GO id)
        go_id = _get_go_id(compartment_tag)
        assert go_id
        # Look up the GO id and extract the name of the GO entity
        compartment_name = get_go_json(go_id)['response']['docs'][0]['annotation_class_label']
        return compartment_name

    # AssertionError -> No annotation containing the GO id
    #                   exists for the SBML compartment tag.
    # ValueError -> An annotation containing the GO id exists
    #               but is an invalid GO id (e.g. FMA:20394)
    except (AssertionError, ValueError):
        name = compartment_tag.attrs['name'] \
            if 'name' in compartment_tag.attrs else compartment_tag.attrs['id']
        close_matches = get_close_matches(name.lower(), all_go_compartments, n=1, cutoff=0.8)
        return close_matches[0] if close_matches else name


def get_all_go_compartments(dirpath):
    """
    Extracts and returns all defined GO compartments from BioModel
    SBML files.

    :param dirpath: Directory containing BioModel SBML files.
    :rtype: set
    """
    from BioModels.tools import get_go_json
    import os

    all_compartments = set()
    for file in os.listdir(dirpath):
        with open(os.path.join(dirpath, file), "r", encoding='utf8') as f:
            soup = BeautifulSoup(f, features='lxml')

            # Skip single-compartment models
            compartment_tags = soup.find_all("compartment")
            if len(compartment_tags) < 2:
                continue

            for tag in compartment_tags:
                try:
                    go_id = tag.find("rdf:li")['rdf:resource'].split('/')[-1]
                    compartment_name = get_go_json(go_id)['response']['docs'][0][
                        'annotation_class_label']
                    all_compartments.add(compartment_name)
                except (ValueError, TypeError):
                    pass
    return all_compartments


def parse_derived_model(sbml_file: TextIO):
    """
    Extracts all parent models from an SBML file and returns a generator of
    (Child Model, Edge, Parent Model) 3-tuples representing parent-child
    relationships between SBML models.

    :param sbml_file: SBML file handle.
    :rtype: generator
    """
    soup = BeautifulSoup(sbml_file, features='lxml')

    child_name = str(basename(sbml_file.name).split('.')[0])
    child_provider = 'biomodels.db'
    child_URI = 'http://identifiers.org/biomodels.db/' + child_name
    child_publication_date = _extract_publication_date(soup)

    for parent_URI in _extract_parent_URIs(soup):
        parent_name = parent_URI.split("http://identifiers.org/")[-1].split('/')[-1]
        parent_provider = parent_URI.split("http://identifiers.org/")[-1].split('/')[0]

        child_data = {
            'name': child_name,
            'provider': child_provider,
            'URI': child_URI,
            'created': child_publication_date
        }
        parent_data = {
            'name': parent_name,
            'provider': parent_provider,
            'URI': parent_URI
        }

        # Color pubmed nodes red, biomodel nodes green
        if parent_data['provider'] in ('biomodels.db', 'pubmed'):
            parent_data['color'] = 'red' if parent_data['provider'] == 'pubmed' else 'green'
        child_data['color'] = 'green'

        yield child_data, 'isDerivedFrom', parent_data


def _extract_parent_URIs(soup: BeautifulSoup):
    for resource in soup.find_all('bqmodel:isderivedfrom'):
        for tag in resource.find_all('rdf:li'):
            yield tag['rdf:resource']


def _extract_publication_date(soup: BeautifulSoup):
    from dateutil import parser

    dt = soup.find("dcterms:created").find("dcterms:w3cdtf").text
    return str(parser.parse(dt).date())


def parse_species_data(sbml_file: TextIO):
    """
    Extracts all species from an SBML file and returns a generator of
    (Model, Edge, Parent Model) 3-tuples each representing a relationship
    between an SBML model and one of its defined species components.

    :param sbml_file: SBML file handle.
    :rtype: generator
    """
    import libsbml

    soup = BeautifulSoup(sbml_file, features='lxml')

    model_name = str(basename(sbml_file.name).split('.')[0])
    model_provider = 'biomodels.db'
    model_URI = 'http://identifiers.org/biomodels.db/' + model_name
    model_publication_date = _extract_publication_date(soup)

    model = libsbml.readSBMLFromFile(sbml_file.name)

    for species in model.getModel().getListOfSpecies():
        species_name = species.getName() if species.getName() else species.getId()

        model_data = {
            'name': model_name,
            'provider': model_provider,
            'URI': model_URI,
            'created': model_publication_date,
            # Color BioModels green
            'color': 'green'
        }

        annotation = species.getAnnotationString()

        species_data = {
            'name': species_name,
            'identifiers': ', '.join(_extract_annotation_identifiers(annotation)),
            # Color Species blue
            'color': 'blue'
        }
        yield species_data, 'isContainedIn', model_data


def _extract_annotation_identifiers(annotation_str: str):
    """
    Returns a generator over all URI identifiers present within
    an SBML annotation.

    :param annotation_str: Valid RDF/XML string with a
                            top-level SBML <annotation> tag.
    """
    soup = BeautifulSoup(annotation_str, features='lxml')
    for tag in soup.find_all(attrs={"rdf:resource": True}):
        yield tag['rdf:resource']
