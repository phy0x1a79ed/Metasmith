Web GUI
############################################################

The web GUI runs a workflow from a shipped template without writing Python. It covers the same
steps as the notebook API: ssh host, agent, data, plan, run and results.

Start it from an empty workspace folder. On first start it copies the tutorials and the standard
library into that folder, so start it from the same folder each time.

.. code-block:: console
    :caption: Terminal

    $ mkdir -p metasmith_ws
    $ cd metasmith_ws
    $ msm gui

The page opens at http://127.0.0.1:8090. It binds to the loopback interface only. Run
``msm gui --help`` for the port, the host and the project folder.

1. Pick a template. The template list shows each template's description.
2. Give each sample its inputs. Type a path or an https URL into each row, or paste a sample
   sheet: a CSV with a header row and one row per sample. With a sheet, pick a column for
   each row that differs per sample. A row you leave typed holds the same value for every
   sample.
3. Deselect any target you do not need.
4. Solve. The GUI shows the plan as a graph of steps.
5. Run it on an agent, then follow its progress and open its results. A plan with a step that
   needs a GPU shows a GPU memory field in the stage and run panel. Enter the memory of one GPU
   on the agent. The field starts at the largest amount any step asks for.

Read :doc:`../workflows/_index` for what each shipped template does.
