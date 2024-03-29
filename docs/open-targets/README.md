# How to submit an Open Targets batch
Batch submission process consists of two major tasks, which are performed asynchronously:
1. [**Manual curation**](../manual-curation/README.md) of trait names should be performed approximately once every two months as new ClinVar versions with new trait names are released. The output of this step is used by the main evidence string generation pipeline.
2. [**Evidence string generation**](generate-evidence-strings.md) is mostly automated and should be run for every Open Targets batch submission.

Additional documentation:
* [Setting up the common environment](environment.md) which is required by both protocols to be able to run
* [Advanced build instructions](build.md), which are not required for batch processing under normal circumstances, because there is already an existing installation of the pipeline on the cluster. These instructions are necessary for the following cases:
  + Installing a newer Python version
  + Clean copying the repository and setting up the package installation from scratch
  + Running the pipeline in non-standard situations, for example when we need to use a version of OLS which has not yet been released
* [Evidence string comparison protocol](../../compare-evidence-strings/): when any significant updates to the code are done, an important control measure is re-running the latest batch using the same input data and the new code, and then doing the comparison to see if the introduced changes are correct.



# Background information

## ClinVar
[ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) is a curated database of clinically relevant genetic variation in humans, maintaned by the National Center for Biotechnology Information in the USA. For each variant, it stores a handful of information, including:
* **Variation location,** e. g.: *NM_007294.3(BRCA1):c.2706delA* (using [HGVS nomenclature](https://varnomen.hgvs.org/) in this example)
* **Gene** which the variant impacts: *BRCA1*
* **Condition** which is associated with this variant: *Hereditary breast and ovarian cancer syndrome*
* **Clinical significance** of the variant. It is most frequently evaluated using the [ACMG guidelines](https://www.acmg.net/docs/standards_guidelines_for_the_interpretation_of_sequence_variants.pdf); however, other approaches also exist. Most common values of this field are:
  * *Pathogenic* generally means that variation is causing the disease or making it worse
  * *Benign*: it has been established that the variant is *not* implicated in this disease
  * *Likely pathogenic* and *Likely benign* have the same meaning as “Pathogenic” and “Benign”, but signify that the connection isn't as certain (usually due to limited information being available for this variant)
  * *Uncertain significance* means that either there is contradictory information on the impact of this variant, or that information is insufficient to draw the conclusion
* **Review status** shows how many submitters provided information for this variant. Example values:
  + no assertion criteria
  + criteria provided, single submitter
  + criteria provided, multiple submitters, no conflicts

ClinVar is continuously updated and holds monthly releases of its database contents.

## Open Targets
[Open Targets](https://www.opentargets.org/) is a collaboration between academia and industry. Among other things, it combines associations between genetic variation and human traits (most notably, diseases) into a single integrated resource. This information is then used to provide evidence on the biological validity of therapeutic targets and an initial assessment of the likely effectiveness of pharmacological intervention on these targets.

Open Targets also holds periodic releases, which happen approximately every two months. Data for every release comes from several data providers. There are several requirements for submitting data to Open Targets:
* It must be represented in the form of “evidence strings”. These are JSON strings describing:
  + Genes the variant affects
  + Functional consequence of the variant on the gene
  + Traits (usually diseases) associated with the variant, such as “parkinson disease” or “age-related macular degeneration”.
  + Other information about the variant and source, such as related publications
* The variant data must be synchronised with a specific version of external data sources, for example Ensembl.

## Role of EVA
ClinVar data is highly valuable, but in its original form is not suitable for submission to Open Targets. EVA is registered as one of the submitters for Open Targets. For every Open Targets release, the EVA processes ClinVar records (variants), curates the result and submits it to Open Targets in the form of evidence strings. This allows for the up-to-date ClinVar data to be integrated into the Open Targets platform.

Approximately one month before the submission deadline, Open Targets will contact their submitters and specify the requirements for the next release. At this point the EVA can start executing the main submission protocol (see below). Once the data is ready, it is submitted to Open Targets, and then the same will happen with the next release. Most of the actions in the pipeline are automated.



# Workflow diagram

```mermaid
graph LR

  subgraph "ClinVar"
    CLINVAR_XML[Full <br> XML]
  end

  subgraph "Manual curation protocol"
    CLINVAR_XML
    --> TRAIT_MAPPING_PIPELINE([Trait <br> mapping <br> pipeline])
    --> AUTOMATED_MAPPINGS[Automated <br> mappings] & MAPPINGS_REQUIRING_CURATION[Mappings <br> requiring <br> curation]

    MAPPINGS_REQUIRING_CURATION
    --> MANUAL_CURATION([Manual <br> curation])
    --> MANUALLY_CURATED_MAPPINGS[Manually curated <br> mappings]

    AUTOMATED_MAPPINGS & MANUALLY_CURATED_MAPPINGS
    --> FINISHED_MAPPINGS[Finished <br> mappings]

    MANUALLY_CURATED_MAPPINGS
    --> SUBMIT_FEEDBACK_TO_EFO([Submit feedback <br> to EFO])
  end

  subgraph "Evidence string generation protocol"
    CLINVAR_XML
    --> PREDICT_CONSEQUENCES_VEP([Predict functional <br> consequences <br> using VEP])

    CLINVAR_XML
    --> PREDICT_CONSEQUENCES_REPEATS([Predict functional <br> consequences <br> for repeats])

    PREDICT_CONSEQUENCES_VEP & PREDICT_CONSEQUENCES_REPEATS
    --> CONSEQUENCES[Functional <br> consequence <br> predictions]

    CLINVAR_XML & CONSEQUENCES & FINISHED_MAPPINGS
    --> EVIDENCE_STRING_GENERATION([Evidence string <br> generation pipeline])
  end

  subgraph End result
    EVIDENCE_STRING_GENERATION
    --> EVIDENCE_STRINGS[Evidence <br> strings] & ZOOMA_FEEDBACK[ZOOMA <br> feedback]
  end

classDef pipeline fill:#0f0

class TRAIT_MAPPING_PIPELINE pipeline
class SUBMIT_FEEDBACK_TO_EFO pipeline
class MANUAL_CURATION pipeline

class CONVERT_CLINVAR pipeline
class PREDICT_CONSEQUENCES_REPEATS pipeline
class PREDICT_CONSEQUENCES_VEP pipeline
class EVIDENCE_STRING_GENERATION pipeline
```

There is also a [presentation](https://docs.google.com/presentation/d/1kr1orv08ZGnPGKNu6vQk4wFYIrufu_iIDf-drCc21vY) describing the workflow in more detail.
