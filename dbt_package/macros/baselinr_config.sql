{% macro baselinr_config(column_name=None, metric=None, threshold=None, **kwargs) %}
  {#
    Helper macro to configure baselinr settings per model or column.
    
    This macro is primarily for documentation and configuration management.
    Actual configuration should be done in baselinr config files or via
    the baselinr_profile and baselinr_drift_test macros.
    
    Args:
        column_name: Optional column name for column-specific config
        metric: Optional metric name
        threshold: Optional threshold value
        **kwargs: Additional configuration options
    
    Usage:
        {{ baselinr_config(column_name='customer_id', metric='count', threshold=10.0) }}
  #}
  
  {%- if execute -%}
    {{ log("baselinr_config: column=" ~ (column_name | default('all')) ~ 
           ", metric=" ~ (metric | default('all')) ~ 
           ", threshold=" ~ (threshold | default('default')), info=True) }}
  {%- endif -%}
  
  -- This macro doesn't execute any SQL, it's for configuration documentation
  SELECT 1 as config_placeholder WHERE 1=0
  
{% endmacro %}

