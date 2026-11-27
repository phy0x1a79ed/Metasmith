Engcyc metagenomics
############################################################

The ``engcyc_metagenomics`` template runs the Engcyc metagenomics workflow on
one or more read sets. Pick it in the GUI, or load its spec from
``src/metasmith_libraries/templates/engcyc_metagenomics/spec.yml``.

The template description lists every lane, its tools and the size of each lane's reference
download. Read it in the GUI's template list, or in ``DESCRIPTION`` in
``src/metasmith_libraries/engcyc_metagenomics.py``.

- The template plans its cases together: short reads, hybrid (short plus long reads),
  long reads, and references. Each read case has its own tab with one example sample.
  Delete each read case you have no samples for. Keep the references case: its targets
  are the built databases.
- Deselect a target to drop its lane. A lane's tools run only for the targets that read it.
- To start a short-read sample from an SRA run instead of read files, change its
  ``read_pair`` row's type to ``ncbi::sra_short_read_accession``, put the run in it,
  for example ``SRR9658108``, and delete its two read rows. Use
  ``ncbi::sra_long_read_accession`` on the ``long_reads`` row for a long-read run.
- For several samples, paste a sample sheet and pick a column for each per-sample row:
  ``sample_name``, ``read_pair`` and the two read rows, or ``sample_name`` and the
  accession row. Leave the other rows as the template types them.
- Give a licensed package and add its target to turn on a licensed lane. The description
  names each one.
- Run ``engcyc_prep_references`` first, once per agent, to fetch every reference database
  ahead of the real run. It takes no samples, and its download steps are the ones
  ``engcyc_metagenomics`` plans, so the real run finds them in the cache.
