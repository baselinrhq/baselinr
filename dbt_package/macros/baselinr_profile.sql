{% macro baselinr_profile(schema_name, table_name, config_path=None, profiling=None) %}
  {#
    Trigger baselinr profiling for a table after model execution.
    
    This macro uses baselinr's profiling with the same configuration
    structure as baselinr config files. The profiling parameter should
    match the profiling section from a baselinr config, with additional
    support for partition and sampling configs that apply to this table.
    
    Args:
        schema_name: Schema name (typically target.schema)
        table_name: Table name (typically target.name)
        config_path: Optional path to baselinr config file (for connection/storage)
        profiling: Dictionary of profiling configuration (optional)
                  If not provided, uses profiling settings from base config file
                  Supports: metrics, compute_histograms, histogram_bins, 
                           max_distinct_values, partition, sampling, etc.
    
    Usage:
        # Using profiling from base config file:
        post-hook: "{{ baselinr_profile(target.schema, target.name) }}"
        
        # Overriding metrics and partition per model:
        post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'metrics': ['count', 'mean', 'stddev'], 'partition': {'key': 'created_date', 'strategy': 'latest'}}) }}"
        
        # With sampling:
        post-hook: "{{ baselinr_profile(target.schema, target.name, profiling={'sampling': {'enabled': true, 'fraction': 0.1}, 'metrics': ['count', 'histogram']}) }}"
        
        # With custom config path:
        post-hook: "{{ baselinr_profile(target.schema, target.name, config_path='baselinr_config.yml', profiling={'metrics': ['count']}) }}"
    
    Note: This macro uses a Python script for profiling. The script must be
    executable and baselinr must be installed. Connection/storage settings come
    from the baselinr config file, while profiling settings can be overridden per model.
  #}
  
  {%- if execute -%}
    {%- set script_path -%}
      {{- var('baselinr_script_path', 'dbt_packages/baselinr/scripts/baselinr_profile.py') -}}
    {%- endset -%}
    {# Note: When installed as a package, the path will be dbt_packages/baselinr/scripts/baselinr_profile.py #}
    
    {%- set config_arg -%}
      {%- if config_path -%}
        --config {{ config_path }}
      {%- endif -%}
    {%- endset -%}
    
    {%- set profiling_arg -%}
      {%- if profiling -%}
        --profiling-config '{{ tojson(profiling) }}'
      {%- endif -%}
    {%- endset -%}
    
    {%- set profile_command -%}
      python {{ script_path }} --schema {{ schema_name }} --table {{ table_name }} {{ config_arg }} {{ profiling_arg }}
    {%- endset -%}
    
    {{ log("Running baselinr profiling for " ~ schema_name ~ "." ~ table_name, info=True) }}
    {{ log("Command: " ~ profile_command, info=True) }}
    
    -- For databases that support it, you can use run_query with the command
    -- For others, use dbt's on-run-end hook in dbt_project.yml:
    -- on-run-end: "python {{ script_path }} --schema {{ target.schema }} --table {{ this }}"
    
    -- Return empty result (actual execution via script)
    SELECT 1 as profiling_triggered WHERE 1=0
    
  {%- endif -%}
{% endmacro %}
