Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/reacton/core.py", line 1900, in _reconsolidate
    effect()
  File "/usr/local/lib/python3.11/site-packages/reacton/core.py", line 1131, in __call__
    self._cleanup = self.callable()
                    ^^^^^^^^^^^^^^^
  File "/code/pages/07_solar_panel.py", line 114, in <lambda>
    lambda: update_map_layer_and_view(m, current_filtered_data, initial_bounds),
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/code/pages/07_solar_panel.py", line 136, in update_map_layer_and_view
    map_instance.add_geojson(
  File "/usr/local/lib/python3.11/site-packages/leafmap/maplibregl.py", line 1600, in add_geojson
    layer = Layer(
            ^^^^^^
  File "/usr/local/lib/python3.11/site-packages/pydantic/main.py", line 250, in __init__
    validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
pydantic_core._pydantic_core.ValidationError: 4 validation errors for Layer
layer_id
  Extra inputs are not permitted [type=extra_forbidden, input_value='GeoAI_Filtered_Solar_Panels', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
color
  Extra inputs are not permitted [type=extra_forbidden, input_value='yellow', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
fill_opacity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.6, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
line_width
  Extra inputs are not permitted [type=extra_forbidden, input_value=1.5, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden