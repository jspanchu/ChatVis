# ChatVis_agent

ChatVis_agent is an LLM agent that aids the LLM to generate Python code for ParaView scientific visualization tasks.
The agent currently uses GPT-5mini as the underlying LLM, but one can easily modify the agent code to call a different LLM.
ChatVis does not require retraining or fine-tuning the LLM.
Instead, ChatVis employs chain-of-thought prompt simplification, retrieval-augmented prompt generation using a vector database of documentation and code examples, and error checking with iterative prompt feedback to correct errors until a visualization is produced.
For now, the agent runs all the test cases included in the benchmark (`run_all.py`).
Using `run_all.py` as an example, one could build an agent to run a single new case from a provided prompt.

## Setup

It is recommended to install dependencies in a virtual Python environment or a Conda environment.

Virtual Python environment (preferred):
```
python -m venv .venv
source .venv/bin/activate
pip3 install <dependencies>     # first time only
cd /path/to/ChatVis_agent
python3 <agent_script>
```

Conda environment:
```
conda activate
pip3 install <dependencies>     # first time only
cd /path/to/ChatVis_agent
python3 <agent_script>
conda deactivate
```

Install dependencies in your environment:
```
pip3 install faiss-cpu    # or faiss-gpu-cu<xx> where <xx> is the CUDA version, eg 11, 12 etc.
pip3 install openai
pip3 install sentence_transformers
```

If you have an Argonne National Laboratory username and are on site or accessing through the VPN, you can use the Argo proxy to access OpenAI through Argo. See the instructions in (https://github.com/Oaklight/argo-proxy) and do the following.
In a new terminal window, open a virtual Python or Conda environment as described above, and then:
```
pip3 install argo-proxy
argo-proxy

# the first time, answer the following:

No valid configuration found. Would you like to create it from config.sample.yaml? [Y/n]: y
Use port [<...>]? [Y/n/<port>]: y
Enter your username: <username>
Enable verbose mode? [Y/n] y

```

Export the following environment variables in the same terminal window where you will run the ChatVis agent:
```
export GEN_CODE_DIR=<existing directory where generated Python code will be placed (absolute full path)>
export GEN_VIS_DIR=<existing directory where generated visualizations will be placed (absolute full path)>
export PATH_TO_PVPYTHON=<path to bin directory where pvpython can be found (absolute full path, excluding pvpython executable, eg. /Applications/ParaView-5.13.1.app/Contents/bin)>
export TOKENIZERS_PARALLELISM=true
export OPENAI_API_KEY=<your OpenAI key or ANL username if using argo-proxy>

# if running argo-proxy:

export OPENAI_BASE_URL=<url from argo-proxy execution:port>/v1 # don't forget to append "/v1", eg http://0.0.0.0:54901/v1
```

## Execution

Run all test cases
```
cd /path/to/ChatVis/ChatVis_agent    # need to be in this directory
python3 ./run_all.py
```

Run one test case
```
cd /path/to/ChatVis/ChatVis_agent           # need to be in this directory
python3 ./run_one.py <path to test case>    # eg /path/to/ChatVis/ChatVis_benchmark/test_cases/canonical_visualizations/ml-iso
```

## Using AGENTS.md with ChatVis_agent

In addition to running predefined benchmark cases, ChatVis_agent can be used interactively via a generic AGENTS.md file (e.g., through a framework such as OpenCode). The AGENTS.md file defines the agent’s behavior and does not require project-specific configuration. To do so, launch OpenCode from within the ChatVis_agent/ directory so it detects AGENTS.md, and provide a prompt that clearly specifies the input data paths, desired output locations, the pvpython path and any runtime arguments, as well as a concise description of the visualization task (e.g., variables to render, filters to apply, timesteps, camera settings, and expected outputs such as screenshots or animations).
