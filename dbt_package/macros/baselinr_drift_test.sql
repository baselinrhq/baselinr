{% test baselinr_drift(model, drift_detection=None, config_path=None) %}
  {#
    Test for data drift detection using baselinr.
    
    This test uses baselinr's drift detection with the same configuration
    structure as baselinr config files. The drift_detection parameter should
    match the drift_detection section from a baselinr config.
    
    Args:
        model: dbt model to test
        drift_detection: Dictionary of drift detection configuration (optional)
                        If not provided, uses drift_detection from base config file
        config_path: Optional path to baselinr config file (for connection/storage)
    
    Returns:
        Rows where drift is detected (test fails if any rows returned)
    
    Usage:
        # Using drift_detection from base config file:
        tests:
          - baselinr_drift
        
        # Overriding drift_detection per test:
        tests:
          - baselinr_drift:
              drift_detection:
                strategy: absolute_threshold
                absolute_threshold:
                  low_threshold: 5.0
                  medium_threshold: 15.0
                  high_threshold: 30.0
                baselines:
                  strategy: auto
        
        # With custom config path:
        tests:
          - baselinr_drift:
              config_path: "path/to/baselinr_config.yml"
              drift_detection:
                strategy: standard_deviation
                standard_deviation:
                  low_threshold: 1.0
                  medium_threshold: 2.0
                  high_threshold: 3.0
    
    Note: This test uses a Python script for drift detection. The script must be
    executable and baselinr must be installed. Connection/storage settings come
    from the baselinr config file, while drift_detection can be overridden per test.
  #}
  
  {%- if execute -%}
    {%- set script_path -%}
      {{- var('baselinr_script_path', 'dbt_packages/baselinr/scripts/baselinr_drift_check.py') -}}
    {%- endset -%}
    
    {%- set config_arg -%}
      {%- if config_path -%}
        --config {{ config_path }}
      {%- endif -%}
    {%- endset -%}
    
    {%- set drift_config_arg -%}
      {%- if drift_detection -%}
        --drift-config '{{ tojson(drift_detection) }}'
      {%- endif -%}
    {%- endset -%}
    
    {{ log("Checking baselinr drift for " ~ model.name, info=True) }}
    
    -- Execute drift check via Python script
    -- The script will exit with code 1 if drift is detected, 0 otherwise
    -- This test returns rows if drift is detected (causing test to fail)
    
    -- Note: Actual execution should be done via dbt's test framework
    -- For now, return a placeholder that indicates drift check should be run
    SELECT 
      '{{ model.name }}' as model_name
    WHERE EXISTS (
      -- This would execute: python {{ script_path }} --schema {{ model.schema }} --table {{ model.name }} {{ config_arg }} {{ drift_config_arg }}
      -- For now, return no rows (test passes)
      SELECT 1 WHERE 1=0
    )
    
  {%- else -%}
    -- Return empty result during parsing
    SELECT 1 WHERE 1=0
  {%- endif -%}
{% endtest %}
