# WAM800-utforsking (ROADMAP oppgave J), kjørt 2026-10-06 23:38 UTC

## Kataloger

- catalog.xml: 0 datasett, 7 underkataloger
- arcticdata/arcticdata.xml: 0 datasett, 17 underkataloger
- metno.xml: 0 datasett, 16 underkataloger
- fou-kl.xml: 0 datasett, 4 underkataloger
- obs.xml: 0 datasett, 10 underkataloger
- fou-hi/fou-hi.xml: 0 datasett, 11 underkataloger
- fou-hi/mywavewam3.xml: 0 datasett, 1 underkataloger []
- fou-hi/mywavewam800current.xml: 0 datasett, 10 underkataloger []
- projects.xml: 0 datasett, 65 underkataloger
- users.xml: 0 datasett, 1 underkataloger
- fou-hi/mywavewam800m/catalog.xml: 4 datasett, 0 underkataloger ['MyWave_wam800_c2SPC00.nc', 'MyWave_wam800_c2SPC12.nc', 'MyWave_wam800_c2WAVE00.nc', 'MyWave_wam800_c2WAVE12.nc']
- fou-hi/mywavewam800n/catalog.xml (gjettet): 4 datasett ['MyWave_wam800_c1SPC00.nc', 'MyWave_wam800_c1SPC12.nc', 'MyWave_wam800_c1WAVE00.nc', 'MyWave_wam800_c1WAVE12.nc']
- fou-hi/mywavewam800s/catalog.xml (gjettet): 4 datasett ['MyWave_wam800_c4SPC00.nc', 'MyWave_wam800_c4SPC12.nc', 'MyWave_wam800_c4WAVE00.nc', 'MyWave_wam800_c4WAVE12.nc']
- fou-hi/mywavewam800v/catalog.xml (gjettet): 4 datasett ['MyWave_wam800_c3SPC00.nc', 'MyWave_wam800_c3SPC12.nc', 'MyWave_wam800_c3WAVE00.nc', 'MyWave_wam800_c3WAVE12.nc']
- fou-hi/mywavewam800f/catalog.xml (gjettet): 4 datasett ['MyWave_wam800_c0SPC00.nc', 'MyWave_wam800_c0SPC12.nc', 'MyWave_wam800_c0WAVE00.nc', 'MyWave_wam800_c0WAVE12.nc']
- Datasett som undersøkes: ['MyWave_wam800_c4WAVE12.nc', 'MyWave_wam800_c4WAVE00.nc', 'MyWave_wam800_c3WAVE12.nc', 'MyWave_wam800_c3WAVE00.nc', 'MyWave_wam800_c2WAVE12.nc', 'MyWave_wam800_c2WAVE00.nc', 'MyWave_wam800_c1WAVE12.nc', 'MyWave_wam800_c1WAVE00.nc', 'MyWave_wam800_c0WAVE12.nc', 'MyWave_wam800_c0WAVE00.nc']

## Retningskonvensjon

WAM800 sine retninger har standard_name `*_to_direction` (retningen bølgene går MOT) - samme som BarentsWatch sin `totalMeanWaveDirection`. Internt i Nordsurf er alt "fra"-retning, så +180 trengs ved en eventuell innkobling. Tallene i tabellene under er RÅ (mot), ikke omregnet.

## Datasett: MyWave_wam800_c4WAVE12.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800s/MyWave_wam800_c4WAVE12.nc
- Tid: 2025-10-07 06:00:00 → 2025-10-10 06:00:00 (73 steg)
- Rutenett: [397, 184] punkter, lat [57.097923278808594, 60.391231536865234], lon [5.548643112182617, 11.821772575378418], våte punkter 28672
- Globale attributter: {"title": "MyWaveWam 800m Skagerrak", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Tue Oct  7 16:00:20 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c4WAVE12.nc\nSat Feb 13 18:27:43 2016: ncatted -a ,global,d,, TRUEcoordDepthc4.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norw
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

## Datasett: MyWave_wam800_c4WAVE00.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800s/MyWave_wam800_c4WAVE00.nc
- Tid: 2025-10-07 18:00:00 → 2025-10-10 18:00:00 (73 steg)
- Rutenett: [397, 184] punkter, lat [57.097923278808594, 60.391231536865234], lon [5.548643112182617, 11.821772575378418], våte punkter 28672
- Globale attributter: {"title": "MyWaveWam 800m Skagerrak", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Wed Oct  8 04:02:15 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c4WAVE00.nc\nSat Feb 13 18:27:43 2016: ncatted -a ,global,d,, TRUEcoordDepthc4.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norw
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

## Datasett: MyWave_wam800_c3WAVE12.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800v/MyWave_wam800_c3WAVE12.nc
- Tid: 2025-10-07 06:00:00 → 2025-10-10 06:00:00 (73 steg)
- Rutenett: [677, 231] punkter, lat [57.932273864746094, 63.6091423034668], lon [2.780068874359131, 8.895548820495605], våte punkter 89579
- Globale attributter: {"title": "MyWaveWam 800m Vestlandet", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Tue Oct  7 16:00:05 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c3WAVE12.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norway as input to applications regarding oil spills, drift of floating o
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon']  /  / meter
  - `latitude` ['rlat', 'rlon'] latitude /  / degree_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degree_east

### Farstadsanden - punkt 62.99287, 7.13199 (0.23 km fra ønsket punkt 1,5 km ut, 1.28 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 2.07 / 11.17 / 109.02 | 2.05 / 11.17 / 109.88 | 0.3 / 3.23 / 57.39 | – | – |
| 2025-10-07T07:00Z | 2.18 / 11.17 / 109.48 | 2.17 / 11.17 / 110.0 | 0.25 / 3.23 / 62.7 | – | – |
| 2025-10-07T08:00Z | 2.27 / 11.17 / 109.98 | 2.25 / 11.17 / 110.63 | 0.31 / 4.74 / 68.67 | – | – |
| 2025-10-07T09:00Z | 2.38 / 11.17 / 110.6 | 2.36 / 11.17 / 111.15 | 0.28 / 4.31 / 62.31 | – | – |
| 2025-10-07T10:00Z | 2.48 / 11.17 / 111.52 | 2.47 / 11.17 / 111.93 | 0.25 / 2.94 / 60.21 | – | – |
| 2025-10-07T11:00Z | 2.62 / 11.17 / 112.42 | 2.6 / 11.17 / 112.87 | 0.29 / 3.56 / 67.45 | – | – |
| 2025-10-07T12:00Z | 2.82 / 12.28 / 113.01 | 2.72 / 12.28 / 114.22 | 0.75 / 6.3 / 96.46 | – | – |
| 2025-10-07T13:00Z | 2.89 / 12.28 / 114.37 | 2.87 / 12.28 / 114.73 | 0.38 / 3.56 / 93.0 | – | – |
| 2025-10-07T14:00Z | 2.9 / 12.28 / 115.3 | 2.89 / 12.28 / 115.53 | 0.26 / 3.56 / 83.59 | – | – |
| 2025-10-07T15:00Z | 2.88 / 12.28 / 115.38 | 2.82 / 12.28 / 116.17 | 0.57 / 4.74 / 95.47 | – | – |
| 2025-10-07T16:00Z | 2.81 / 12.28 / 115.16 | 2.74 / 12.28 / 116.24 | 0.66 / 5.21 / 95.9 | – | – |
| 2025-10-07T17:00Z | 2.73 / 12.28 / 114.97 | 2.68 / 12.28 / 115.82 | 0.52 / 4.31 / 91.41 | – | – |
| 2025-10-07T18:00Z | 2.63 / 12.28 / 114.89 | 2.59 / 12.28 / 115.59 | 0.41 / 3.91 / 85.09 | – | – |
| 2025-10-07T19:00Z | 2.54 / 12.28 / 114.88 | 2.5 / 12.28 / 115.67 | 0.43 / 4.31 / 86.71 | – | – |
| 2025-10-07T20:00Z | 2.45 / 12.28 / 114.96 | 2.43 / 12.28 / 115.5 | 0.31 / 3.91 / 79.13 | – | – |
| 2025-10-07T21:00Z | 2.37 / 12.28 / 115.19 | 2.37 / 12.28 / 115.3 | 0.12 / 2.43 / 51.97 | – | – |
| 2025-10-07T22:00Z | 2.32 / 12.28 / 115.33 | 2.31 / 12.28 / 115.51 | 0.15 / 2.67 / 61.17 | – | – |
| 2025-10-07T23:00Z | 2.28 / 12.28 / 115.59 | 2.27 / 12.28 / 115.77 | 0.14 / 2.43 / 55.26 | – | – |
| 2025-10-08T00:00Z | 2.28 / 12.28 / 115.8 | 2.27 / 12.28 / 115.97 | 0.14 / 2.43 / 57.37 | – | – |
| 2025-10-08T01:00Z | 2.31 / 12.28 / 116.05 | 2.3 / 12.28 / 116.24 | 0.15 / 2.94 / 50.98 | – | – |
| 2025-10-08T02:00Z | 2.35 / 12.28 / 116.36 | 2.35 / 12.28 / 116.42 | 0.08 / 2.01 / 44.55 | – | – |
| 2025-10-08T03:00Z | 2.38 / 12.28 / 116.53 | 2.38 / 12.28 / 116.62 | 0.11 / 1.37 / 44.13 | – | – |
| 2025-10-08T04:00Z | 2.39 / 12.28 / 116.64 | 2.38 / 12.28 / 116.84 | 0.15 / 1.66 / 40.84 | – | – |
| 2025-10-08T05:00Z | 2.37 / 12.28 / 116.72 | 2.37 / 12.28 / 116.86 | 0.13 / 1.66 / 36.97 | – | – |
| 2025-10-08T06:00Z | 2.35 / 12.28 / 116.5 | 2.35 / 12.28 / 116.77 | 0.18 / 1.66 / 39.05 | – | – |
| 2025-10-08T07:00Z | 2.36 / 11.17 / 115.62 | 2.35 / 11.17 / 116.12 | 0.24 / 1.83 / 41.98 | – | – |
| 2025-10-08T08:00Z | 2.51 / 11.17 / 114.32 | 2.49 / 11.17 / 114.86 | 0.27 / 3.56 / 48.05 | – | – |
| 2025-10-08T09:00Z | 2.72 / 11.17 / 113.31 | 2.47 / 11.17 / 117.19 | 1.14 / 6.93 / 95.09 | – | – |
| 2025-10-08T10:00Z | 2.93 / 11.17 / 113.25 | 2.69 / 11.17 / 116.37 | 1.16 / 6.3 / 96.38 | – | – |
| 2025-10-08T11:00Z | 3.03 / 11.17 / 114.07 | 2.65 / 11.17 / 118.53 | 1.47 / 7.63 / 99.44 | – | – |
| 2025-10-08T12:00Z | 3.07 / 11.17 / 114.97 | 2.78 / 11.17 / 118.18 | 1.28 / 6.93 / 99.77 | – | – |
| 2025-10-08T13:00Z | 3.01 / 11.17 / 115.94 | 2.85 / 11.17 / 118.38 | 0.98 / 6.93 / 95.32 | – | – |
| 2025-10-08T14:00Z | 2.93 / 11.17 / 116.82 | 2.76 / 11.17 / 119.19 | 0.99 / 6.3 / 98.03 | – | – |
| 2025-10-08T15:00Z | 2.86 / 11.17 / 117.39 | 2.71 / 11.17 / 119.62 | 0.91 / 6.93 / 97.41 | – | – |
| 2025-10-08T16:00Z | 2.76 / 11.17 / 117.89 | 2.67 / 11.17 / 119.67 | 0.69 / 5.73 / 91.07 | – | – |
| 2025-10-08T17:00Z | 2.66 / 11.17 / 118.32 | 2.61 / 11.17 / 119.71 | 0.54 / 5.73 / 85.38 | – | – |
| 2025-10-08T18:00Z | 2.56 / 11.17 / 118.9 | 2.55 / 11.17 / 119.14 | 0.19 / 2.94 / 63.06 | – | – |
| 2025-10-08T19:00Z | 2.46 / 12.28 / 119.56 | 2.46 / 12.28 / 119.62 | 0.09 / 1.37 / 38.57 | – | – |
| 2025-10-08T20:00Z | 2.36 / 12.28 / 120.17 | 2.36 / 12.28 / 120.27 | 0.11 / 1.37 / 31.76 | – | – |
| 2025-10-08T21:00Z | 2.28 / 12.28 / 120.42 | 2.27 / 12.28 / 120.67 | 0.17 / 1.66 / 37.08 | – | – |
| 2025-10-08T22:00Z | 2.24 / 12.28 / 119.68 | 2.23 / 12.28 / 120.26 | 0.24 / 1.83 / 38.46 | – | – |
| 2025-10-08T23:00Z | 2.27 / 11.17 / 118.24 | 2.24 / 11.17 / 119.36 | 0.34 / 4.31 / 46.37 | – | – |
| 2025-10-09T00:00Z | 2.3 / 11.17 / 117.26 | 2.27 / 11.17 / 118.5 | 0.36 / 4.31 / 47.35 | – | – |
| 2025-10-09T01:00Z | 2.4 / 11.17 / 115.75 | 2.35 / 11.17 / 117.66 | 0.49 / 6.3 / 61.71 | – | – |
| 2025-10-09T02:00Z | 2.64 / 11.17 / 113.94 | 2.55 / 11.17 / 116.35 | 0.71 / 6.3 / 82.24 | – | – |
| 2025-10-09T03:00Z | 2.85 / 11.17 / 113.06 | 2.52 / 11.17 / 119.39 | 1.33 / 9.23 / 90.83 | – | – |
| 2025-10-09T04:00Z | 2.91 / 11.17 / 113.57 | 2.56 / 11.17 / 120.04 | 1.4 / 8.39 / 92.21 | – | – |
| 2025-10-09T05:00Z | 2.97 / 11.17 / 114.31 | 2.68 / 11.17 / 118.98 | 1.29 / 7.63 / 94.52 | – | – |

## Datasett: MyWave_wam800_c3WAVE00.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800v/MyWave_wam800_c3WAVE00.nc
- Tid: 2025-10-07 18:00:00 → 2025-10-10 18:00:00 (73 steg)
- Rutenett: [677, 231] punkter, lat [57.932273864746094, 63.6091423034668], lon [2.780068874359131, 8.895548820495605], våte punkter 89579
- Globale attributter: {"title": "MyWaveWam 800m Vestlandet", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Wed Oct  8 04:01:59 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c3WAVE00.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norway as input to applications regarding oil spills, drift of floating o
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon']  /  / meter
  - `latitude` ['rlat', 'rlon'] latitude /  / degree_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degree_east

- farstadsanden: dekkes også her (0.23 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c3WAVE12.nc
## Datasett: MyWave_wam800_c2WAVE12.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800m/MyWave_wam800_c2WAVE12.nc
- Tid: 2025-10-07 06:00:00 → 2025-10-10 06:00:00 (73 steg)
- Rutenett: [688, 178] punkter, lat [62.33359146118164, 67.82959747314453], lon [7.018731117248535, 16.2911319732666], våte punkter 61115
- Globale attributter: {"title": "MyWaveWam 800m MidtNorge", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Tue Oct  7 15:59:22 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c2WAVE12.nc\nSat Feb 13 18:25:44 2016: ncatted -a ,global,d,, TRUEcoordDepthc2.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norw
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

- farstadsanden: dekkes også her (0.37 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c3WAVE12.nc
## Datasett: MyWave_wam800_c2WAVE00.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800m/MyWave_wam800_c2WAVE00.nc
- Tid: 2025-10-07 18:00:00 → 2025-10-10 18:00:00 (73 steg)
- Rutenett: [688, 178] punkter, lat [62.33359146118164, 67.82959747314453], lon [7.018731117248535, 16.2911319732666], våte punkter 61115
- Globale attributter: {"title": "MyWaveWam 800m MidtNorge", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Wed Oct  8 04:01:16 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c2WAVE00.nc\nSat Feb 13 18:25:44 2016: ncatted -a ,global,d,, TRUEcoordDepthc2.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norw
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

- farstadsanden: dekkes også her (0.37 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c3WAVE12.nc
## Datasett: MyWave_wam800_c1WAVE12.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800n/MyWave_wam800_c1WAVE12.nc
- Tid: 2025-10-07 06:00:00 → 2025-10-10 06:00:00 (73 steg)
- Rutenett: [952, 228] punkter, lat [66.12361145019531, 72.00888061523438], lon [9.490080833435059, 29.698686599731445], våte punkter 110304
- Globale attributter: {"title": "MyWaveWam 800m NordNorge", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Tue Oct  7 15:58:45 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c1WAVE12.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for all coastal areas in Norway as input to applications regarding oil spills, drift of floating ob
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

### Grøtfjord - punkt 69.78553, 18.48971 (0.41 km fra ønsket punkt 1,5 km ut, 1.9 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 1.19 / 9.23 / 112.67 | 1.11 / 9.23 / 117.6 | 0.43 / 2.43 / 332.85 | – | – |
| 2025-10-07T07:00Z | 1.25 / 9.23 / 113.04 | 1.17 / 9.23 / 117.64 | 0.44 / 2.43 / 332.92 | – | – |
| 2025-10-07T08:00Z | 1.29 / 9.23 / 113.27 | 1.21 / 9.23 / 117.58 | 0.44 / 2.67 / 333.05 | – | – |
| 2025-10-07T09:00Z | 1.32 / 9.23 / 113.39 | 1.24 / 9.23 / 117.5 | 0.43 / 2.43 / 335.38 | – | – |
| 2025-10-07T10:00Z | 1.34 / 9.23 / 113.5 | 1.27 / 9.23 / 117.39 | 0.42 / 2.43 / 338.41 | – | – |
| 2025-10-07T11:00Z | 1.34 / 9.23 / 114.56 | 1.3 / 9.23 / 117.24 | 0.34 / 2.43 / 343.27 | – | – |
| 2025-10-07T12:00Z | 1.37 / 10.15 / 114.84 | 1.33 / 10.15 / 117.06 | 0.33 / 2.43 / 340.73 | – | – |
| 2025-10-07T13:00Z | 1.43 / 10.15 / 114.29 | 1.38 / 10.15 / 116.84 | 0.36 / 2.43 / 344.55 | – | – |
| 2025-10-07T14:00Z | 1.5 / 10.15 / 114.36 | 1.46 / 10.15 / 116.7 | 0.35 / 2.43 / 350.43 | – | – |
| 2025-10-07T15:00Z | 1.56 / 10.15 / 115.05 | 1.53 / 10.15 / 116.82 | 0.32 / 2.21 / 351.64 | – | – |
| 2025-10-07T16:00Z | 1.64 / 10.15 / 115.66 | 1.61 / 10.15 / 117.08 | 0.29 / 2.21 / 357.68 | – | – |
| 2025-10-07T17:00Z | 1.75 / 10.15 / 116.75 | 1.74 / 10.15 / 117.35 | 0.21 / 2.01 / 1.62 | – | – |
| 2025-10-07T18:00Z | 1.85 / 10.15 / 117.42 | 1.84 / 10.15 / 117.75 | 0.2 / 3.91 / 84.59 | – | – |
| 2025-10-07T19:00Z | 1.96 / 10.15 / 117.41 | 1.95 / 10.15 / 117.75 | 0.21 / 3.56 / 79.37 | – | – |
| 2025-10-07T20:00Z | 2.04 / 10.15 / 117.64 | 2.03 / 10.15 / 117.74 | 0.1 / 1.51 / 57.88 | – | – |
| 2025-10-07T21:00Z | 2.07 / 10.15 / 117.91 | 2.07 / 10.15 / 117.96 | 0.07 / 1.25 / 39.1 | – | – |
| 2025-10-07T22:00Z | 2.08 / 11.17 / 118.23 | 2.08 / 11.17 / 118.31 | 0.09 / 1.37 / 25.39 | – | – |
| 2025-10-07T23:00Z | 2.1 / 11.17 / 118.59 | 2.1 / 11.17 / 118.69 | 0.1 / 1.37 / 17.59 | – | – |
| 2025-10-08T00:00Z | 2.14 / 11.17 / 118.93 | 2.14 / 11.17 / 119.05 | 0.11 / 1.51 / 10.74 | – | – |
| 2025-10-08T01:00Z | 2.21 / 12.28 / 119.28 | 2.21 / 12.28 / 119.41 | 0.12 / 1.51 / 6.88 | – | – |
| 2025-10-08T02:00Z | 2.28 / 12.28 / 119.55 | 2.28 / 12.28 / 119.71 | 0.14 / 1.66 / 2.04 | – | – |
| 2025-10-08T03:00Z | 2.32 / 12.28 / 119.72 | 2.31 / 12.28 / 119.94 | 0.17 / 1.66 / 0.03 | – | – |
| 2025-10-08T04:00Z | 2.34 / 12.28 / 119.83 | 2.33 / 12.28 / 120.07 | 0.18 / 1.83 / 358.16 | – | – |
| 2025-10-08T05:00Z | 2.37 / 12.28 / 119.9 | 2.36 / 12.28 / 120.14 | 0.18 / 1.83 / 0.99 | – | – |
| 2025-10-08T06:00Z | 2.4 / 12.28 / 119.99 | 2.39 / 12.28 / 120.17 | 0.16 / 1.66 / 0.61 | – | – |
| 2025-10-08T07:00Z | 2.41 / 12.28 / 120.0 | 2.41 / 12.28 / 120.12 | 0.13 / 1.66 / 0.56 | – | – |
| 2025-10-08T08:00Z | 2.4 / 12.28 / 120.05 | 2.39 / 12.28 / 120.15 | 0.11 / 1.51 / 3.41 | – | – |
| 2025-10-08T09:00Z | 2.34 / 12.28 / 120.09 | 2.34 / 12.28 / 120.15 | 0.09 / 1.51 / 0.42 | – | – |
| 2025-10-08T10:00Z | 2.28 / 12.28 / 120.04 | 2.28 / 12.28 / 120.09 | 0.08 / 1.37 / 359.3 | – | – |
| 2025-10-08T11:00Z | 2.21 / 12.28 / 119.96 | 2.21 / 12.28 / 120.01 | 0.08 / 1.37 / 1.26 | – | – |
| 2025-10-08T12:00Z | 2.15 / 12.28 / 119.87 | 2.15 / 12.28 / 119.91 | 0.07 / 1.37 / 1.01 | – | – |
| 2025-10-08T13:00Z | 2.08 / 12.28 / 119.78 | 2.08 / 12.28 / 119.8 | 0.05 / 1.25 / 2.47 | – | – |
| 2025-10-08T14:00Z | 2.03 / 12.28 / 119.69 | 2.03 / 12.28 / 119.69 | 0.02 / 1.03 / 347.79 | – | – |
| 2025-10-08T15:00Z | 1.97 / 12.28 / 119.64 | 1.97 / 12.28 / 119.64 | 0.0 / 1.0 / 53.53 | – | – |
| 2025-10-08T16:00Z | 1.93 / 12.28 / 119.6 | 1.93 / 12.28 / 119.6 | 0.01 / 1.03 / 308.71 | – | – |
| 2025-10-08T17:00Z | 1.89 / 12.28 / 119.6 | 1.89 / 12.28 / 119.6 | 0.01 / 1.03 / 317.16 | – | – |
| 2025-10-08T18:00Z | 1.86 / 12.28 / 119.61 | 1.86 / 12.28 / 119.61 | 0.01 / 1.03 / 320.45 | – | – |
| 2025-10-08T19:00Z | 1.84 / 12.28 / 119.67 | 1.84 / 12.28 / 119.67 | 0.02 / 1.03 / 334.09 | – | – |
| 2025-10-08T20:00Z | 1.82 / 12.28 / 119.75 | 1.82 / 12.28 / 119.75 | 0.03 / 1.03 / 331.21 | – | – |
| 2025-10-08T21:00Z | 1.8 / 12.28 / 119.79 | 1.8 / 12.28 / 119.83 | 0.08 / 1.25 / 339.94 | – | – |
| 2025-10-08T22:00Z | 1.79 / 12.28 / 119.86 | 1.79 / 12.28 / 119.92 | 0.08 / 1.37 / 344.07 | – | – |
| 2025-10-08T23:00Z | 1.76 / 12.28 / 119.94 | 1.76 / 12.28 / 120.0 | 0.07 / 1.37 / 346.86 | – | – |
| 2025-10-09T00:00Z | 1.74 / 12.28 / 120.0 | 1.73 / 12.28 / 120.06 | 0.07 / 1.37 / 348.6 | – | – |
| 2025-10-09T01:00Z | 1.71 / 12.28 / 119.98 | 1.71 / 12.28 / 120.08 | 0.09 / 1.37 / 349.77 | – | – |
| 2025-10-09T02:00Z | 1.69 / 12.28 / 119.93 | 1.69 / 12.28 / 120.03 | 0.09 / 1.51 / 352.4 | – | – |
| 2025-10-09T03:00Z | 1.7 / 12.28 / 119.73 | 1.7 / 12.28 / 119.81 | 0.08 / 1.37 / 354.99 | – | – |
| 2025-10-09T04:00Z | 1.73 / 12.28 / 119.45 | 1.73 / 12.28 / 119.52 | 0.07 / 1.37 / 4.93 | – | – |
| 2025-10-09T05:00Z | 1.72 / 12.28 / 119.67 | 1.72 / 12.28 / 119.7 | 0.05 / 1.25 / 355.31 | – | – |

### Tromvik - punkt 69.78865, 18.42541 (0.41 km fra ønsket punkt 1,5 km ut, 1.27 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 1.34 / 9.23 / 122.94 | 1.31 / 9.23 / 123.41 | 0.28 / 2.43 / 314.96 | – | – |
| 2025-10-07T07:00Z | 1.41 / 9.23 / 122.95 | 1.38 / 9.23 / 123.43 | 0.28 / 2.43 / 316.52 | – | – |
| 2025-10-07T08:00Z | 1.46 / 9.23 / 122.9 | 1.43 / 9.23 / 123.37 | 0.28 / 2.43 / 316.97 | – | – |
| 2025-10-07T09:00Z | 1.49 / 9.23 / 122.9 | 1.46 / 9.23 / 123.33 | 0.26 / 2.43 / 319.48 | – | – |
| 2025-10-07T10:00Z | 1.51 / 9.23 / 122.82 | 1.49 / 9.23 / 123.22 | 0.23 / 1.83 / 322.22 | – | – |
| 2025-10-07T11:00Z | 1.53 / 10.15 / 122.79 | 1.52 / 10.15 / 123.06 | 0.17 / 1.66 / 328.63 | – | – |
| 2025-10-07T12:00Z | 1.57 / 10.15 / 122.75 | 1.56 / 10.15 / 122.94 | 0.16 / 1.66 / 325.46 | – | – |
| 2025-10-07T13:00Z | 1.64 / 10.15 / 122.5 | 1.63 / 10.15 / 122.71 | 0.17 / 1.66 / 327.55 | – | – |
| 2025-10-07T14:00Z | 1.73 / 10.15 / 122.3 | 1.72 / 10.15 / 122.55 | 0.16 / 1.51 / 341.25 | – | – |
| 2025-10-07T15:00Z | 1.82 / 10.15 / 122.53 | 1.81 / 10.15 / 122.81 | 0.17 / 1.66 / 349.99 | – | – |
| 2025-10-07T16:00Z | 1.94 / 10.15 / 122.92 | 1.93 / 10.15 / 123.31 | 0.19 / 1.66 / 7.64 | – | – |
| 2025-10-07T17:00Z | 2.1 / 10.15 / 123.57 | 2.1 / 10.15 / 123.82 | 0.16 / 1.66 / 20.93 | – | – |
| 2025-10-07T18:00Z | 2.26 / 10.15 / 124.42 | 2.23 / 10.15 / 125.0 | 0.32 / 5.21 / 93.61 | – | – |
| 2025-10-07T19:00Z | 2.42 / 10.15 / 124.94 | 2.41 / 10.15 / 125.24 | 0.22 / 3.23 / 84.54 | – | – |
| 2025-10-07T20:00Z | 2.52 / 10.15 / 125.49 | 2.52 / 10.15 / 125.6 | 0.13 / 2.21 / 76.4 | – | – |
| 2025-10-07T21:00Z | 2.58 / 11.17 / 126.13 | 2.58 / 11.17 / 126.16 | 0.07 / 1.37 / 62.23 | – | – |
| 2025-10-07T22:00Z | 2.62 / 11.17 / 126.89 | 2.62 / 11.17 / 126.93 | 0.08 / 1.13 / 60.43 | – | – |
| 2025-10-07T23:00Z | 2.67 / 11.17 / 127.7 | 2.67 / 11.17 / 127.75 | 0.1 / 1.25 / 50.28 | – | – |
| 2025-10-08T00:00Z | 2.77 / 12.28 / 128.57 | 2.77 / 12.28 / 128.63 | 0.1 / 1.37 / 38.68 | – | – |
| 2025-10-08T01:00Z | 2.91 / 12.28 / 129.46 | 2.91 / 12.28 / 129.51 | 0.1 / 1.37 / 31.85 | – | – |
| 2025-10-08T02:00Z | 3.04 / 12.28 / 130.21 | 3.03 / 12.28 / 130.26 | 0.1 / 1.37 / 21.09 | – | – |
| 2025-10-08T03:00Z | 3.1 / 12.28 / 130.7 | 3.1 / 12.28 / 130.76 | 0.11 / 1.51 / 16.23 | – | – |
| 2025-10-08T04:00Z | 3.14 / 12.28 / 130.93 | 3.14 / 12.28 / 130.98 | 0.11 / 1.51 / 12.12 | – | – |
| 2025-10-08T05:00Z | 3.18 / 12.28 / 131.01 | 3.18 / 12.28 / 131.06 | 0.11 / 1.37 / 14.59 | – | – |
| 2025-10-08T06:00Z | 3.21 / 12.28 / 131.01 | 3.21 / 12.28 / 131.06 | 0.1 / 1.37 / 18.3 | – | – |
| 2025-10-08T07:00Z | 3.23 / 12.28 / 130.91 | 3.22 / 12.28 / 130.94 | 0.09 / 1.37 / 18.12 | – | – |
| 2025-10-08T08:00Z | 3.19 / 12.28 / 130.9 | 3.19 / 12.28 / 130.94 | 0.1 / 1.37 / 18.98 | – | – |
| 2025-10-08T09:00Z | 3.11 / 12.28 / 130.85 | 3.11 / 12.28 / 130.87 | 0.08 / 1.25 / 13.01 | – | – |
| 2025-10-08T10:00Z | 3.01 / 12.28 / 130.68 | 3.01 / 12.28 / 130.7 | 0.08 / 1.25 / 6.56 | – | – |
| 2025-10-08T11:00Z | 2.91 / 12.28 / 130.47 | 2.91 / 12.28 / 130.5 | 0.08 / 1.25 / 8.33 | – | – |
| 2025-10-08T12:00Z | 2.81 / 12.28 / 130.29 | 2.81 / 12.28 / 130.31 | 0.07 / 1.25 / 8.12 | – | – |
| 2025-10-08T13:00Z | 2.71 / 12.28 / 130.12 | 2.71 / 12.28 / 130.14 | 0.06 / 1.13 / 9.5 | – | – |
| 2025-10-08T14:00Z | 2.63 / 12.28 / 130.03 | 2.63 / 12.28 / 130.03 | 0.02 / 1.03 / 349.45 | – | – |
| 2025-10-08T15:00Z | 2.56 / 12.28 / 129.98 | 2.56 / 12.28 / 129.98 | 0.0 / 1.0 / 53.48 | – | – |
| 2025-10-08T16:00Z | 2.5 / 12.28 / 129.98 | 2.5 / 12.28 / 129.98 | 0.0 / 1.0 / 53.48 | – | – |
| 2025-10-08T17:00Z | 2.45 / 12.28 / 129.99 | 2.45 / 12.28 / 129.99 | 0.0 / 1.0 / 53.48 | – | – |
| 2025-10-08T18:00Z | 2.42 / 12.28 / 130.05 | 2.42 / 12.28 / 130.05 | 0.01 / 1.03 / 321.55 | – | – |
| 2025-10-08T19:00Z | 2.4 / 12.28 / 130.19 | 2.4 / 12.28 / 130.19 | 0.01 / 1.03 / 355.07 | – | – |
| 2025-10-08T20:00Z | 2.38 / 12.28 / 130.38 | 2.38 / 12.28 / 130.38 | 0.01 / 1.03 / 333.0 | – | – |
| 2025-10-08T21:00Z | 2.36 / 12.28 / 130.53 | 2.36 / 12.28 / 130.53 | 0.01 / 1.03 / 341.43 | – | – |
| 2025-10-08T22:00Z | 2.34 / 12.28 / 130.67 | 2.34 / 12.28 / 130.67 | 0.01 / 1.03 / 344.02 | – | – |
| 2025-10-08T23:00Z | 2.32 / 12.28 / 130.82 | 2.32 / 12.28 / 130.82 | 0.01 / 1.03 / 13.1 | – | – |
| 2025-10-09T00:00Z | 2.28 / 12.28 / 130.93 | 2.28 / 12.28 / 130.93 | 0.02 / 1.03 / 339.24 | – | – |
| 2025-10-09T01:00Z | 2.25 / 12.28 / 130.98 | 2.25 / 12.28 / 130.98 | 0.03 / 1.03 / 337.41 | – | – |
| 2025-10-09T02:00Z | 2.22 / 12.28 / 130.93 | 2.22 / 12.28 / 130.94 | 0.05 / 1.03 / 0.49 | – | – |
| 2025-10-09T03:00Z | 2.24 / 12.28 / 130.54 | 2.23 / 12.28 / 130.59 | 0.08 / 1.25 / 41.45 | – | – |
| 2025-10-09T04:00Z | 2.28 / 12.28 / 130.26 | 2.28 / 12.28 / 130.33 | 0.09 / 1.25 / 63.88 | – | – |
| 2025-10-09T05:00Z | 2.27 / 12.28 / 130.83 | 2.27 / 12.28 / 130.83 | 0.03 / 1.03 / 35.6 | – | – |

### Ersfjordstranda - punkt 69.49189, 17.36944 (0.21 km fra ønsket punkt 1,5 km ut, 1.46 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 1.36 / 9.23 / 121.06 | 1.35 / 9.23 / 121.31 | 0.12 / 1.66 / 341.18 | – | – |
| 2025-10-07T07:00Z | 1.39 / 9.23 / 120.98 | 1.38 / 9.23 / 121.27 | 0.13 / 1.66 / 343.42 | – | – |
| 2025-10-07T08:00Z | 1.42 / 9.23 / 120.77 | 1.41 / 9.23 / 121.18 | 0.16 / 1.66 / 346.86 | – | – |
| 2025-10-07T09:00Z | 1.46 / 9.23 / 120.31 | 1.44 / 9.23 / 121.09 | 0.22 / 1.83 / 348.16 | – | – |
| 2025-10-07T10:00Z | 1.51 / 9.23 / 119.87 | 1.49 / 9.23 / 121.04 | 0.27 / 2.01 / 350.34 | – | – |
| 2025-10-07T11:00Z | 1.57 / 10.15 / 119.86 | 1.54 / 10.15 / 120.97 | 0.28 / 2.01 / 346.99 | – | – |
| 2025-10-07T12:00Z | 1.61 / 10.15 / 119.94 | 1.59 / 10.15 / 120.94 | 0.27 / 2.01 / 347.56 | – | – |
| 2025-10-07T13:00Z | 1.67 / 10.15 / 119.93 | 1.64 / 10.15 / 121.01 | 0.28 / 2.01 / 352.03 | – | – |
| 2025-10-07T14:00Z | 1.73 / 10.15 / 120.49 | 1.72 / 10.15 / 121.23 | 0.24 / 2.01 / 357.55 | – | – |
| 2025-10-07T15:00Z | 1.85 / 10.15 / 120.37 | 1.83 / 10.15 / 121.61 | 0.3 / 2.21 / 18.44 | – | – |
| 2025-10-07T16:00Z | 1.95 / 10.15 / 120.64 | 1.92 / 10.15 / 121.86 | 0.31 / 2.43 / 31.16 | – | – |
| 2025-10-07T17:00Z | 2.06 / 10.15 / 121.41 | 2.04 / 10.15 / 122.13 | 0.25 / 2.21 / 42.11 | – | – |
| 2025-10-07T18:00Z | 2.27 / 10.15 / 121.92 | 2.24 / 10.15 / 122.72 | 0.35 / 4.74 / 81.74 | – | – |
| 2025-10-07T19:00Z | 2.39 / 10.15 / 122.62 | 2.39 / 10.15 / 122.94 | 0.21 / 2.01 / 66.41 | – | – |
| 2025-10-07T20:00Z | 2.41 / 11.17 / 123.19 | 2.4 / 11.17 / 123.55 | 0.23 / 2.01 / 67.3 | – | – |
| 2025-10-07T21:00Z | 2.42 / 11.17 / 123.79 | 2.41 / 11.17 / 124.1 | 0.2 / 2.01 / 57.51 | – | – |
| 2025-10-07T22:00Z | 2.46 / 11.17 / 124.65 | 2.45 / 11.17 / 124.86 | 0.17 / 1.83 / 48.14 | – | – |
| 2025-10-07T23:00Z | 2.55 / 11.17 / 125.64 | 2.55 / 11.17 / 125.79 | 0.15 / 1.83 / 42.0 | – | – |
| 2025-10-08T00:00Z | 2.7 / 12.28 / 126.6 | 2.69 / 12.28 / 126.69 | 0.12 / 1.66 / 30.49 | – | – |
| 2025-10-08T01:00Z | 2.81 / 12.28 / 127.22 | 2.81 / 12.28 / 127.28 | 0.1 / 1.51 / 15.41 | – | – |
| 2025-10-08T02:00Z | 2.85 / 12.28 / 127.4 | 2.85 / 12.28 / 127.45 | 0.1 / 1.51 / 6.31 | – | – |
| 2025-10-08T03:00Z | 2.86 / 12.28 / 127.31 | 2.86 / 12.28 / 127.36 | 0.11 / 1.51 / 3.42 | – | – |
| 2025-10-08T04:00Z | 2.88 / 12.28 / 127.12 | 2.88 / 12.28 / 127.2 | 0.12 / 1.66 / 8.09 | – | – |
| 2025-10-08T05:00Z | 2.91 / 12.28 / 126.95 | 2.91 / 12.28 / 127.01 | 0.11 / 1.66 / 15.47 | – | – |
| 2025-10-08T06:00Z | 2.93 / 12.28 / 126.89 | 2.92 / 12.28 / 126.93 | 0.09 / 1.51 / 8.08 | – | – |
| 2025-10-08T07:00Z | 2.91 / 12.28 / 126.78 | 2.91 / 12.28 / 126.81 | 0.09 / 1.51 / 0.45 | – | – |
| 2025-10-08T08:00Z | 2.84 / 12.28 / 126.51 | 2.84 / 12.28 / 126.54 | 0.08 / 1.51 / 356.43 | – | – |
| 2025-10-08T09:00Z | 2.74 / 12.28 / 126.2 | 2.74 / 12.28 / 126.24 | 0.08 / 1.51 / 359.0 | – | – |
| 2025-10-08T10:00Z | 2.64 / 12.28 / 125.88 | 2.63 / 12.28 / 125.93 | 0.09 / 1.51 / 3.57 | – | – |
| 2025-10-08T11:00Z | 2.54 / 12.28 / 125.61 | 2.54 / 12.28 / 125.66 | 0.09 / 1.51 / 8.2 | – | – |
| 2025-10-08T12:00Z | 2.45 / 12.28 / 125.41 | 2.45 / 12.28 / 125.46 | 0.08 / 1.51 / 7.43 | – | – |
| 2025-10-08T13:00Z | 2.37 / 12.28 / 125.26 | 2.37 / 12.28 / 125.3 | 0.08 / 1.37 / 3.49 | – | – |
| 2025-10-08T14:00Z | 2.31 / 12.28 / 125.19 | 2.31 / 12.28 / 125.21 | 0.06 / 1.37 / 2.05 | – | – |
| 2025-10-08T15:00Z | 2.25 / 12.28 / 125.14 | 2.25 / 12.28 / 125.17 | 0.07 / 1.25 / 354.58 | – | – |
| 2025-10-08T16:00Z | 2.22 / 12.28 / 125.2 | 2.22 / 12.28 / 125.22 | 0.06 / 1.25 / 354.66 | – | – |
| 2025-10-08T17:00Z | 2.2 / 12.28 / 125.33 | 2.2 / 12.28 / 125.34 | 0.06 / 1.25 / 344.94 | – | – |
| 2025-10-08T18:00Z | 2.18 / 12.28 / 125.5 | 2.18 / 12.28 / 125.51 | 0.05 / 1.25 / 348.55 | – | – |
| 2025-10-08T19:00Z | 2.16 / 12.28 / 125.65 | 2.16 / 12.28 / 125.67 | 0.07 / 1.25 / 342.09 | – | – |
| 2025-10-08T20:00Z | 2.14 / 12.28 / 125.8 | 2.14 / 12.28 / 125.82 | 0.07 / 1.25 / 333.58 | – | – |
| 2025-10-08T21:00Z | 2.11 / 12.28 / 125.93 | 2.11 / 12.28 / 125.96 | 0.08 / 1.37 / 334.52 | – | – |
| 2025-10-08T22:00Z | 2.08 / 12.28 / 126.05 | 2.08 / 12.28 / 126.08 | 0.07 / 1.37 / 341.9 | – | – |
| 2025-10-08T23:00Z | 2.05 / 12.28 / 126.13 | 2.05 / 12.28 / 126.19 | 0.1 / 1.51 / 342.77 | – | – |
| 2025-10-09T00:00Z | 2.03 / 12.28 / 126.16 | 2.02 / 12.28 / 126.25 | 0.11 / 1.51 / 348.67 | – | – |
| 2025-10-09T01:00Z | 2.02 / 12.28 / 126.21 | 2.02 / 12.28 / 126.28 | 0.08 / 1.51 / 14.74 | – | – |
| 2025-10-09T02:00Z | 2.05 / 12.28 / 125.87 | 2.02 / 12.28 / 126.52 | 0.3 / 4.74 / 93.63 | – | – |
| 2025-10-09T03:00Z | 2.05 / 12.28 / 126.0 | 2.05 / 12.28 / 126.3 | 0.18 / 2.21 / 74.7 | – | – |
| 2025-10-09T04:00Z | 2.0 / 12.28 / 126.56 | 2.0 / 12.28 / 126.65 | 0.09 / 1.66 / 48.12 | – | – |
| 2025-10-09T05:00Z | 1.94 / 12.28 / 126.97 | 1.94 / 12.28 / 126.98 | 0.04 / 1.37 / 14.88 | – | – |

### Russelv - punkt 69.95564, 20.19544 (0.29 km fra ønsket punkt 1,5 km ut, 1.23 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 0.31 / 2.21 / 357.36 | 0.09 / 13.51 / 194.98 | 0.3 / 2.21 / 358.46 | – | – |
| 2025-10-07T07:00Z | 0.25 / 2.21 / 5.11 | 0.1 / 13.51 / 210.43 | 0.23 / 2.21 / 6.98 | – | – |
| 2025-10-07T08:00Z | 0.19 / 2.01 / 24.34 | 0.15 / 12.28 / 29.99 | 0.12 / 2.01 / 21.56 | – | – |
| 2025-10-07T09:00Z | 0.19 / 12.28 / 49.01 | 0.14 / 12.28 / 86.64 | 0.13 / 2.43 / 33.79 | – | – |
| 2025-10-07T10:00Z | 0.21 / 12.28 / 52.11 | 0.17 / 12.28 / 64.04 | 0.12 / 1.66 / 41.07 | – | – |
| 2025-10-07T11:00Z | 0.22 / 12.28 / 49.97 | 0.16 / 12.28 / 78.72 | 0.15 / 2.43 / 35.15 | – | – |
| 2025-10-07T12:00Z | 0.21 / 12.28 / 53.08 | 0.18 / 12.28 / 65.84 | 0.11 / 1.66 / 33.62 | – | – |
| 2025-10-07T13:00Z | 0.19 / 12.28 / 62.24 | 0.19 / 12.28 / 62.22 | 0.01 / 1.03 / 75.42 | – | – |
| 2025-10-07T14:00Z | 0.18 / 12.28 / 73.74 | 0.18 / 12.28 / 73.74 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-07T15:00Z | 0.2 / 12.28 / 66.08 | 0.18 / 12.28 / 75.85 | 0.07 / 1.37 / 29.62 | – | – |
| 2025-10-07T16:00Z | 0.35 / 2.94 / 49.17 | 0.13 / 12.28 / 152.7 | 0.33 / 2.94 / 43.36 | – | – |
| 2025-10-07T17:00Z | 0.44 / 3.23 / 47.82 | 0.14 / 12.28 / 145.55 | 0.42 / 3.23 / 43.23 | – | – |
| 2025-10-07T18:00Z | 0.42 / 3.23 / 49.58 | 0.16 / 12.28 / 130.72 | 0.38 / 3.23 / 42.05 | – | – |
| 2025-10-07T19:00Z | 0.4 / 12.28 / 44.93 | 0.15 / 12.28 / 144.1 | 0.37 / 2.94 / 36.61 | – | – |
| 2025-10-07T20:00Z | 0.34 / 12.28 / 63.89 | 0.17 / 12.28 / 146.43 | 0.3 / 2.94 / 51.47 | – | – |
| 2025-10-07T21:00Z | 0.3 / 12.28 / 86.57 | 0.19 / 12.28 / 159.47 | 0.24 / 2.67 / 53.06 | – | – |
| 2025-10-07T22:00Z | 0.31 / 12.28 / 104.38 | 0.21 / 12.28 / 163.28 | 0.22 / 2.43 / 50.86 | – | – |
| 2025-10-07T23:00Z | 0.3 / 12.28 / 126.33 | 0.24 / 12.28 / 161.15 | 0.18 / 2.43 / 47.67 | – | – |
| 2025-10-08T00:00Z | 0.3 / 12.28 / 143.94 | 0.26 / 12.28 / 159.57 | 0.14 / 2.21 / 37.44 | – | – |
| 2025-10-08T01:00Z | 0.34 / 13.51 / 145.26 | 0.28 / 13.51 / 165.74 | 0.19 / 2.01 / 35.76 | – | – |
| 2025-10-08T02:00Z | 0.38 / 13.51 / 149.64 | 0.33 / 13.51 / 165.74 | 0.2 / 2.21 / 31.97 | – | – |
| 2025-10-08T03:00Z | 0.43 / 13.51 / 156.78 | 0.38 / 13.51 / 167.06 | 0.19 / 2.21 / 27.96 | – | – |
| 2025-10-08T04:00Z | 0.48 / 13.51 / 158.81 | 0.43 / 13.51 / 167.79 | 0.2 / 2.43 / 29.24 | – | – |
| 2025-10-08T05:00Z | 0.51 / 13.51 / 160.01 | 0.47 / 13.51 / 166.9 | 0.2 / 2.21 / 27.14 | – | – |
| 2025-10-08T06:00Z | 0.51 / 13.51 / 161.54 | 0.48 / 13.51 / 167.14 | 0.18 / 2.43 / 29.51 | – | – |
| 2025-10-08T07:00Z | 0.5 / 13.51 / 163.31 | 0.47 / 13.51 / 169.48 | 0.18 / 2.43 / 36.8 | – | – |
| 2025-10-08T08:00Z | 0.49 / 12.28 / 165.68 | 0.48 / 12.28 / 167.69 | 0.12 / 1.83 / 28.73 | – | – |
| 2025-10-08T09:00Z | 0.49 / 12.28 / 167.56 | 0.49 / 12.28 / 167.56 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T10:00Z | 0.47 / 12.28 / 169.79 | 0.47 / 12.28 / 169.8 | 0.02 / 1.03 / 84.96 | – | – |
| 2025-10-08T11:00Z | 0.45 / 12.28 / 171.05 | 0.45 / 12.28 / 171.05 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T12:00Z | 0.44 / 12.28 / 171.95 | 0.44 / 12.28 / 171.95 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T13:00Z | 0.43 / 12.28 / 172.53 | 0.43 / 12.28 / 172.53 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T14:00Z | 0.42 / 12.28 / 172.98 | 0.42 / 12.28 / 172.98 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T15:00Z | 0.42 / 12.28 / 173.34 | 0.42 / 12.28 / 173.34 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T16:00Z | 0.42 / 12.28 / 173.68 | 0.42 / 12.28 / 173.68 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T17:00Z | 0.43 / 12.28 / 173.97 | 0.43 / 12.28 / 173.97 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T18:00Z | 0.44 / 12.28 / 174.25 | 0.44 / 12.28 / 174.25 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T19:00Z | 0.45 / 12.28 / 174.53 | 0.45 / 12.28 / 174.53 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T20:00Z | 0.46 / 12.28 / 174.8 | 0.46 / 12.28 / 174.8 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T21:00Z | 0.46 / 12.28 / 175.02 | 0.46 / 12.28 / 175.02 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T22:00Z | 0.47 / 12.28 / 175.21 | 0.47 / 12.28 / 175.21 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-08T23:00Z | 0.47 / 11.17 / 175.39 | 0.47 / 11.17 / 175.39 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-09T00:00Z | 0.48 / 13.51 / 175.64 | 0.48 / 13.51 / 175.64 | 0.0 / 1.0 / 55.1 | – | – |
| 2025-10-09T01:00Z | 0.49 / 13.51 / 176.01 | 0.49 / 13.51 / 176.01 | 0.01 / 1.03 / 9.47 | – | – |
| 2025-10-09T02:00Z | 0.51 / 13.51 / 175.85 | 0.5 / 13.51 / 176.39 | 0.1 / 1.13 / 31.46 | – | – |
| 2025-10-09T03:00Z | 0.54 / 13.51 / 174.96 | 0.52 / 13.51 / 176.48 | 0.13 / 1.51 / 28.44 | – | – |
| 2025-10-09T04:00Z | 0.6 / 13.51 / 168.39 | 0.54 / 13.51 / 176.34 | 0.25 / 2.21 / 38.49 | – | – |
| 2025-10-09T05:00Z | 0.65 / 13.51 / 161.63 | 0.57 / 13.51 / 175.35 | 0.31 / 2.67 / 42.5 | – | – |

### Lenangsøyra - punkt 69.85925, 19.99392 (0.35 km fra ønsket punkt 1,5 km ut, 1.31 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 0.2 / 2.43 / 34.4 | 0.19 / 2.43 / 35.68 | 0.06 / 1.37 / 18.33 | – | – |
| 2025-10-07T07:00Z | 0.22 / 2.43 / 32.96 | 0.16 / 2.43 / 28.09 | 0.14 / 2.21 / 38.55 | – | – |
| 2025-10-07T08:00Z | 0.24 / 2.67 / 38.62 | 0.19 / 2.67 / 36.0 | 0.15 / 2.21 / 42.86 | – | – |
| 2025-10-07T09:00Z | 0.28 / 2.94 / 39.0 | 0.17 / 2.94 / 43.36 | 0.22 / 2.67 / 36.58 | – | – |
| 2025-10-07T10:00Z | 0.29 / 2.94 / 38.35 | 0.19 / 2.94 / 40.36 | 0.22 / 2.67 / 36.98 | – | – |
| 2025-10-07T11:00Z | 0.3 / 2.94 / 37.59 | 0.16 / 3.23 / 48.21 | 0.26 / 2.67 / 33.97 | – | – |
| 2025-10-07T12:00Z | 0.29 / 2.94 / 37.64 | 0.13 / 3.23 / 46.29 | 0.25 / 2.67 / 35.74 | – | – |
| 2025-10-07T13:00Z | 0.24 / 2.67 / 35.54 | 0.14 / 2.94 / 38.41 | 0.2 / 2.43 / 34.37 | – | – |
| 2025-10-07T14:00Z | 0.26 / 2.67 / 36.44 | 0.07 / 3.56 / 75.18 | 0.25 / 2.67 / 34.63 | – | – |
| 2025-10-07T15:00Z | 0.35 / 2.67 / 38.66 | 0.05 / 12.28 / 137.59 | 0.35 / 2.67 / 38.09 | – | – |
| 2025-10-07T16:00Z | 0.43 / 2.94 / 35.94 | 0.07 / 13.51 / 116.71 | 0.43 / 2.94 / 35.05 | – | – |
| 2025-10-07T17:00Z | 0.45 / 2.94 / 34.34 | 0.07 / 13.51 / 115.71 | 0.44 / 2.94 / 33.58 | – | – |
| 2025-10-07T18:00Z | 0.41 / 2.94 / 30.76 | 0.08 / 13.51 / 106.48 | 0.4 / 2.94 / 29.62 | – | – |
| 2025-10-07T19:00Z | 0.38 / 2.67 / 30.63 | 0.07 / 13.51 / 122.43 | 0.38 / 2.67 / 29.92 | – | – |
| 2025-10-07T20:00Z | 0.29 / 2.67 / 40.3 | 0.16 / 2.94 / 16.19 | 0.24 / 2.67 / 48.75 | – | – |
| 2025-10-07T21:00Z | 0.21 / 2.43 / 59.62 | 0.2 / 2.43 / 58.78 | 0.08 / 1.51 / 65.22 | – | – |
| 2025-10-07T22:00Z | 0.17 / 2.21 / 71.69 | 0.16 / 2.21 / 75.71 | 0.06 / 1.37 / 31.98 | – | – |
| 2025-10-07T23:00Z | 0.15 / 13.51 / 68.06 | 0.12 / 13.51 / 86.16 | 0.08 / 1.37 / 23.5 | – | – |
| 2025-10-08T00:00Z | 0.15 / 13.51 / 58.23 | 0.11 / 13.51 / 94.37 | 0.11 / 2.01 / 26.25 | – | – |
| 2025-10-08T01:00Z | 0.17 / 13.51 / 45.56 | 0.1 / 13.51 / 124.9 | 0.13 / 2.01 / 23.53 | – | – |
| 2025-10-08T02:00Z | 0.18 / 13.51 / 43.74 | 0.11 / 13.51 / 142.31 | 0.14 / 2.01 / 18.13 | – | – |
| 2025-10-08T03:00Z | 0.19 / 14.86 / 45.97 | 0.12 / 14.86 / 173.14 | 0.15 / 1.66 / 16.78 | – | – |
| 2025-10-08T04:00Z | 0.2 / 14.86 / 87.19 | 0.14 / 14.86 / 181.7 | 0.15 / 1.66 / 18.44 | – | – |
| 2025-10-08T05:00Z | 0.21 / 14.86 / 142.59 | 0.15 / 14.86 / 185.06 | 0.15 / 1.66 / 20.06 | – | – |
| 2025-10-08T06:00Z | 0.22 / 13.51 / 145.19 | 0.16 / 13.51 / 186.5 | 0.15 / 1.83 / 24.7 | – | – |
| 2025-10-08T07:00Z | 0.22 / 13.51 / 148.92 | 0.17 / 13.51 / 182.28 | 0.14 / 1.83 / 22.88 | – | – |
| 2025-10-08T08:00Z | 0.21 / 13.51 / 156.88 | 0.16 / 13.51 / 182.41 | 0.13 / 1.83 / 24.22 | – | – |
| 2025-10-08T09:00Z | 0.21 / 13.51 / 158.54 | 0.16 / 13.51 / 185.34 | 0.13 / 1.83 / 28.5 | – | – |
| 2025-10-08T10:00Z | 0.2 / 13.51 / 164.41 | 0.16 / 13.51 / 186.18 | 0.12 / 1.83 / 34.74 | – | – |
| 2025-10-08T11:00Z | 0.17 / 13.51 / 177.22 | 0.17 / 13.51 / 178.23 | 0.03 / 1.13 / 45.97 | – | – |
| 2025-10-08T12:00Z | 0.16 / 13.51 / 184.47 | 0.16 / 13.51 / 184.47 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T13:00Z | 0.15 / 13.51 / 186.61 | 0.15 / 13.51 / 186.61 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T14:00Z | 0.14 / 13.51 / 187.4 | 0.14 / 13.51 / 187.4 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T15:00Z | 0.14 / 13.51 / 187.88 | 0.14 / 13.51 / 187.88 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T16:00Z | 0.15 / 13.51 / 188.21 | 0.15 / 13.51 / 188.21 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T17:00Z | 0.15 / 13.51 / 188.48 | 0.15 / 13.51 / 188.48 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T18:00Z | 0.16 / 13.51 / 188.66 | 0.16 / 13.51 / 188.66 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T19:00Z | 0.16 / 13.51 / 188.82 | 0.16 / 13.51 / 188.82 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T20:00Z | 0.17 / 13.51 / 188.96 | 0.17 / 13.51 / 188.96 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T21:00Z | 0.17 / 13.51 / 189.09 | 0.17 / 13.51 / 189.09 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T22:00Z | 0.18 / 14.86 / 189.23 | 0.18 / 14.86 / 189.23 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-08T23:00Z | 0.18 / 14.86 / 189.39 | 0.18 / 14.86 / 189.39 | 0.0 / 1.0 / 54.9 | – | – |
| 2025-10-09T00:00Z | 0.19 / 14.86 / 189.55 | 0.19 / 14.86 / 189.55 | 0.0 / 1.03 / 45.13 | – | – |
| 2025-10-09T01:00Z | 0.2 / 13.51 / 189.66 | 0.2 / 13.51 / 189.69 | 0.01 / 1.03 / 30.19 | – | – |
| 2025-10-09T02:00Z | 0.22 / 13.51 / 186.35 | 0.2 / 13.51 / 189.77 | 0.09 / 1.25 / 34.42 | – | – |
| 2025-10-09T03:00Z | 0.27 / 13.51 / 177.98 | 0.22 / 13.51 / 189.16 | 0.15 / 1.83 / 27.1 | – | – |
| 2025-10-09T04:00Z | 0.37 / 13.51 / 66.79 | 0.23 / 13.51 / 189.15 | 0.29 / 2.21 / 28.56 | – | – |
| 2025-10-09T05:00Z | 0.4 / 13.51 / 61.07 | 0.26 / 13.51 / 185.36 | 0.31 / 2.43 / 25.57 | – | – |

### Steinkrøssa - punkt 69.50087, 17.29211 (0.25 km fra ønsket punkt 1,5 km ut, 1.66 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 1.41 / 9.23 / 117.43 | 1.39 / 9.23 / 118.27 | 0.23 / 2.01 / 336.5 | – | – |
| 2025-10-07T07:00Z | 1.44 / 9.23 / 117.11 | 1.42 / 9.23 / 118.11 | 0.26 / 2.01 / 336.23 | – | – |
| 2025-10-07T08:00Z | 1.48 / 9.23 / 116.67 | 1.45 / 9.23 / 117.9 | 0.28 / 2.01 / 337.76 | – | – |
| 2025-10-07T09:00Z | 1.52 / 9.23 / 116.01 | 1.48 / 9.23 / 117.72 | 0.34 / 2.21 / 336.55 | – | – |
| 2025-10-07T10:00Z | 1.56 / 9.23 / 115.82 | 1.52 / 9.23 / 117.55 | 0.35 / 2.43 / 337.28 | – | – |
| 2025-10-07T11:00Z | 1.61 / 10.15 / 115.82 | 1.58 / 10.15 / 117.35 | 0.35 / 2.43 / 335.7 | – | – |
| 2025-10-07T12:00Z | 1.67 / 10.15 / 115.78 | 1.63 / 10.15 / 117.25 | 0.35 / 2.43 / 334.72 | – | – |
| 2025-10-07T13:00Z | 1.72 / 10.15 / 115.99 | 1.68 / 10.15 / 117.31 | 0.34 / 2.43 / 337.84 | – | – |
| 2025-10-07T14:00Z | 1.81 / 10.15 / 116.11 | 1.77 / 10.15 / 117.55 | 0.34 / 2.43 / 347.53 | – | – |
| 2025-10-07T15:00Z | 1.93 / 10.15 / 116.01 | 1.89 / 10.15 / 118.08 | 0.41 / 2.43 / 0.98 | – | – |
| 2025-10-07T16:00Z | 2.03 / 10.15 / 116.71 | 1.99 / 10.15 / 118.39 | 0.38 / 2.43 / 9.73 | – | – |
| 2025-10-07T17:00Z | 2.15 / 10.15 / 117.96 | 2.12 / 10.15 / 118.93 | 0.32 / 2.21 / 45.5 | – | – |
| 2025-10-07T18:00Z | 2.38 / 10.15 / 119.07 | 2.35 / 10.15 / 119.89 | 0.38 / 4.74 / 81.86 | – | – |
| 2025-10-07T19:00Z | 2.5 / 10.15 / 120.25 | 2.49 / 10.15 / 120.62 | 0.24 / 3.91 / 66.05 | – | – |
| 2025-10-07T20:00Z | 2.51 / 11.17 / 121.15 | 2.5 / 11.17 / 121.63 | 0.27 / 4.31 / 64.93 | – | – |
| 2025-10-07T21:00Z | 2.53 / 11.17 / 122.02 | 2.52 / 11.17 / 122.48 | 0.26 / 3.91 / 53.35 | – | – |
| 2025-10-07T22:00Z | 2.59 / 11.17 / 123.3 | 2.58 / 11.17 / 123.64 | 0.22 / 1.83 / 38.47 | – | – |
| 2025-10-07T23:00Z | 2.71 / 12.28 / 124.86 | 2.71 / 12.28 / 125.12 | 0.2 / 1.83 / 32.23 | – | – |
| 2025-10-08T00:00Z | 2.89 / 12.28 / 126.4 | 2.88 / 12.28 / 126.52 | 0.15 / 1.83 / 14.69 | – | – |
| 2025-10-08T01:00Z | 3.02 / 12.28 / 127.44 | 3.02 / 12.28 / 127.5 | 0.13 / 1.66 / 359.01 | – | – |
| 2025-10-08T02:00Z | 3.07 / 12.28 / 127.74 | 3.06 / 12.28 / 127.81 | 0.14 / 1.66 / 352.91 | – | – |
| 2025-10-08T03:00Z | 3.08 / 12.28 / 127.55 | 3.07 / 12.28 / 127.63 | 0.15 / 1.83 / 350.86 | – | – |
| 2025-10-08T04:00Z | 3.09 / 12.28 / 127.19 | 3.08 / 12.28 / 127.33 | 0.19 / 1.83 / 358.06 | – | – |
| 2025-10-08T05:00Z | 3.11 / 12.28 / 126.9 | 3.11 / 12.28 / 127.02 | 0.18 / 1.83 / 358.72 | – | – |
| 2025-10-08T06:00Z | 3.12 / 12.28 / 126.87 | 3.12 / 12.28 / 126.94 | 0.14 / 1.83 / 353.71 | – | – |
| 2025-10-08T07:00Z | 3.09 / 12.28 / 126.74 | 3.09 / 12.28 / 126.79 | 0.13 / 1.66 / 351.39 | – | – |
| 2025-10-08T08:00Z | 3.0 / 12.28 / 126.37 | 3.0 / 12.28 / 126.42 | 0.12 / 1.66 / 348.44 | – | – |
| 2025-10-08T09:00Z | 2.89 / 12.28 / 125.97 | 2.89 / 12.28 / 126.03 | 0.12 / 1.66 / 351.28 | – | – |
| 2025-10-08T10:00Z | 2.78 / 12.28 / 125.6 | 2.77 / 12.28 / 125.68 | 0.13 / 1.66 / 352.2 | – | – |
| 2025-10-08T11:00Z | 2.67 / 12.28 / 125.37 | 2.67 / 12.28 / 125.46 | 0.13 / 1.66 / 354.68 | – | – |
| 2025-10-08T12:00Z | 2.58 / 12.28 / 125.32 | 2.58 / 12.28 / 125.38 | 0.11 / 1.66 / 355.11 | – | – |
| 2025-10-08T13:00Z | 2.51 / 12.28 / 125.39 | 2.51 / 12.28 / 125.44 | 0.1 / 1.51 / 352.22 | – | – |
| 2025-10-08T14:00Z | 2.45 / 12.28 / 125.59 | 2.45 / 12.28 / 125.63 | 0.09 / 1.51 / 349.44 | – | – |
| 2025-10-08T15:00Z | 2.41 / 12.28 / 125.82 | 2.4 / 12.28 / 125.85 | 0.07 / 1.51 / 345.43 | – | – |
| 2025-10-08T16:00Z | 2.38 / 12.28 / 126.12 | 2.38 / 12.28 / 126.14 | 0.07 / 1.37 / 343.03 | – | – |
| 2025-10-08T17:00Z | 2.36 / 12.28 / 126.49 | 2.36 / 12.28 / 126.52 | 0.07 / 1.37 / 340.48 | – | – |
| 2025-10-08T18:00Z | 2.35 / 12.28 / 126.86 | 2.35 / 12.28 / 126.89 | 0.07 / 1.37 / 338.19 | – | – |
| 2025-10-08T19:00Z | 2.33 / 12.28 / 127.15 | 2.33 / 12.28 / 127.17 | 0.08 / 1.37 / 334.65 | – | – |
| 2025-10-08T20:00Z | 2.31 / 12.28 / 127.39 | 2.31 / 12.28 / 127.43 | 0.1 / 1.51 / 329.93 | – | – |
| 2025-10-08T21:00Z | 2.29 / 12.28 / 127.69 | 2.28 / 12.28 / 127.73 | 0.1 / 1.51 / 330.5 | – | – |
| 2025-10-08T22:00Z | 2.26 / 12.28 / 128.15 | 2.26 / 12.28 / 128.18 | 0.1 / 1.51 / 333.36 | – | – |
| 2025-10-08T23:00Z | 2.25 / 12.28 / 128.71 | 2.25 / 12.28 / 128.77 | 0.11 / 1.51 / 334.03 | – | – |
| 2025-10-09T00:00Z | 2.24 / 12.28 / 129.26 | 2.24 / 12.28 / 129.35 | 0.14 / 1.66 / 337.04 | – | – |
| 2025-10-09T01:00Z | 2.26 / 12.28 / 129.76 | 2.26 / 12.28 / 129.94 | 0.15 / 3.56 / 58.8 | – | – |
| 2025-10-09T02:00Z | 2.32 / 12.28 / 129.96 | 2.29 / 12.28 / 130.98 | 0.39 / 4.74 / 93.27 | – | – |
| 2025-10-09T03:00Z | 2.35 / 12.28 / 131.0 | 2.34 / 12.28 / 131.39 | 0.22 / 2.94 / 76.86 | – | – |
| 2025-10-09T04:00Z | 2.32 / 12.28 / 132.51 | 2.32 / 12.28 / 132.62 | 0.11 / 1.51 / 39.03 | – | – |
| 2025-10-09T05:00Z | 2.27 / 12.28 / 133.91 | 2.27 / 12.28 / 133.94 | 0.06 / 1.37 / 2.33 | – | – |

### Unstad - punkt 68.27590, 13.55867 (0.46 km fra ønsket punkt 1,5 km ut, 1.17 km fra spoten)

| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |
|---|---|---|---|---|---|
| 2025-10-07T06:00Z | 2.54 / 9.23 / 88.17 | 2.44 / 9.23 / 92.05 | 0.71 / 5.21 / 27.96 | – | – |
| 2025-10-07T07:00Z | 2.55 / 9.23 / 86.82 | 2.39 / 9.23 / 92.68 | 0.9 / 4.74 / 37.16 | – | – |
| 2025-10-07T08:00Z | 2.52 / 9.23 / 86.12 | 2.32 / 9.23 / 93.25 | 0.99 / 5.21 / 39.92 | – | – |
| 2025-10-07T09:00Z | 2.56 / 9.23 / 85.57 | 2.28 / 9.23 / 94.62 | 1.16 / 6.93 / 46.65 | – | – |
| 2025-10-07T10:00Z | 2.66 / 9.23 / 85.9 | 2.36 / 9.23 / 94.82 | 1.22 / 5.21 / 49.68 | – | – |
| 2025-10-07T11:00Z | 2.8 / 9.23 / 87.64 | 2.53 / 9.23 / 95.41 | 1.2 / 6.93 / 50.56 | – | – |
| 2025-10-07T12:00Z | 2.95 / 10.15 / 90.41 | 2.75 / 10.15 / 95.99 | 1.06 / 6.3 / 49.21 | – | – |
| 2025-10-07T13:00Z | 3.11 / 10.15 / 92.82 | 2.91 / 10.15 / 97.93 | 1.08 / 6.3 / 53.26 | – | – |
| 2025-10-07T14:00Z | 3.29 / 10.15 / 94.71 | 2.94 / 10.15 / 102.66 | 1.49 / 7.63 / 62.79 | – | – |
| 2025-10-07T15:00Z | 3.43 / 10.15 / 98.23 | 3.18 / 10.15 / 103.33 | 1.28 / 6.3 / 65.3 | – | – |
| 2025-10-07T16:00Z | 3.5 / 10.15 / 101.25 | 3.34 / 10.15 / 104.78 | 1.04 / 5.73 / 63.12 | – | – |
| 2025-10-07T17:00Z | 3.53 / 11.17 / 103.41 | 3.43 / 11.17 / 105.94 | 0.86 / 5.21 / 60.02 | – | – |
| 2025-10-07T18:00Z | 3.59 / 11.17 / 105.24 | 3.49 / 11.17 / 107.69 | 0.84 / 5.21 / 59.15 | – | – |
| 2025-10-07T19:00Z | 3.68 / 11.17 / 107.1 | 3.62 / 11.17 / 108.71 | 0.66 / 4.74 / 53.03 | – | – |
| 2025-10-07T20:00Z | 3.79 / 11.17 / 108.68 | 3.73 / 11.17 / 110.27 | 0.67 / 4.74 / 52.1 | – | – |
| 2025-10-07T21:00Z | 3.87 / 12.28 / 109.79 | 3.81 / 12.28 / 111.44 | 0.69 / 4.74 / 51.43 | – | – |
| 2025-10-07T22:00Z | 3.93 / 12.28 / 110.49 | 3.88 / 12.28 / 111.97 | 0.65 / 5.21 / 48.46 | – | – |
| 2025-10-07T23:00Z | 3.98 / 12.28 / 110.62 | 3.93 / 12.28 / 112.02 | 0.64 / 5.21 / 47.42 | – | – |
| 2025-10-08T00:00Z | 4.04 / 12.28 / 110.4 | 3.97 / 12.28 / 112.09 | 0.72 / 4.74 / 48.84 | – | – |
| 2025-10-08T01:00Z | 4.09 / 12.28 / 110.34 | 4.04 / 12.28 / 111.65 | 0.64 / 5.21 / 48.23 | – | – |
| 2025-10-08T02:00Z | 4.12 / 12.28 / 110.78 | 4.1 / 12.28 / 111.44 | 0.45 / 3.91 / 42.17 | – | – |
| 2025-10-08T03:00Z | 4.13 / 12.28 / 111.57 | 4.12 / 12.28 / 111.92 | 0.32 / 3.23 / 36.46 | – | – |
| 2025-10-08T04:00Z | 4.07 / 12.28 / 112.37 | 4.06 / 12.28 / 112.6 | 0.26 / 3.23 / 32.87 | – | – |
| 2025-10-08T05:00Z | 3.96 / 12.28 / 112.82 | 3.96 / 12.28 / 112.96 | 0.2 / 2.67 / 28.36 | – | – |
| 2025-10-08T06:00Z | 3.82 / 12.28 / 112.78 | 3.81 / 12.28 / 112.99 | 0.24 / 3.23 / 32.2 | – | – |
| 2025-10-08T07:00Z | 3.66 / 12.28 / 112.34 | 3.65 / 12.28 / 112.52 | 0.21 / 2.94 / 29.95 | – | – |
| 2025-10-08T08:00Z | 3.5 / 12.28 / 112.07 | 3.49 / 12.28 / 112.54 | 0.33 / 3.56 / 42.01 | – | – |
| 2025-10-08T09:00Z | 3.37 / 12.28 / 111.73 | 3.34 / 12.28 / 112.73 | 0.46 / 4.74 / 45.47 | – | – |
| 2025-10-08T10:00Z | 3.26 / 12.28 / 111.42 | 3.23 / 12.28 / 112.45 | 0.45 / 4.31 / 36.34 | – | – |
| 2025-10-08T11:00Z | 3.19 / 12.28 / 111.33 | 3.16 / 12.28 / 112.23 | 0.41 / 3.91 / 37.34 | – | – |
| 2025-10-08T12:00Z | 3.15 / 12.28 / 110.8 | 3.11 / 12.28 / 112.27 | 0.52 / 3.91 / 39.27 | – | – |
| 2025-10-08T13:00Z | 3.11 / 12.28 / 110.63 | 3.06 / 12.28 / 112.17 | 0.52 / 4.74 / 34.59 | – | – |
| 2025-10-08T14:00Z | 3.06 / 12.28 / 111.0 | 3.03 / 12.28 / 112.12 | 0.43 / 3.91 / 32.49 | – | – |
| 2025-10-08T15:00Z | 3.02 / 12.28 / 110.92 | 2.98 / 12.28 / 112.54 | 0.52 / 4.74 / 38.33 | – | – |
| 2025-10-08T16:00Z | 3.0 / 12.28 / 110.54 | 2.96 / 12.28 / 112.01 | 0.49 / 3.91 / 27.51 | – | – |
| 2025-10-08T17:00Z | 2.98 / 12.28 / 109.97 | 2.95 / 12.28 / 111.01 | 0.41 / 3.23 / 26.74 | – | – |
| 2025-10-08T18:00Z | 2.99 / 12.28 / 110.42 | 2.97 / 12.28 / 111.06 | 0.33 / 3.91 / 21.93 | – | – |
| 2025-10-08T19:00Z | 2.93 / 12.28 / 112.48 | 2.91 / 12.28 / 112.81 | 0.27 / 3.23 / 68.18 | – | – |
| 2025-10-08T20:00Z | 2.84 / 12.28 / 114.28 | 2.84 / 12.28 / 114.27 | 0.18 / 2.43 / 119.29 | – | – |
| 2025-10-08T21:00Z | 2.77 / 12.28 / 115.66 | 2.73 / 12.28 / 116.05 | 0.48 / 3.91 / 103.08 | – | – |
| 2025-10-08T22:00Z | 2.73 / 12.28 / 116.64 | 2.66 / 12.28 / 117.94 | 0.61 / 4.31 / 91.04 | – | – |
| 2025-10-08T23:00Z | 2.7 / 12.28 / 117.4 | 2.64 / 12.28 / 119.41 | 0.59 / 4.74 / 74.81 | – | – |
| 2025-10-09T00:00Z | 2.67 / 12.28 / 118.15 | 2.64 / 12.28 / 119.5 | 0.42 / 3.56 / 58.44 | – | – |
| 2025-10-09T01:00Z | 2.63 / 12.28 / 119.49 | 2.63 / 12.28 / 119.62 | 0.13 / 2.01 / 26.6 | – | – |
| 2025-10-09T02:00Z | 2.59 / 12.28 / 120.84 | 2.58 / 12.28 / 120.88 | 0.08 / 1.83 / 13.75 | – | – |
| 2025-10-09T03:00Z | 2.54 / 12.28 / 121.9 | 2.54 / 12.28 / 121.94 | 0.09 / 1.37 / 3.86 | – | – |
| 2025-10-09T04:00Z | 2.5 / 12.28 / 122.45 | 2.48 / 12.28 / 123.36 | 0.31 / 3.91 / 33.1 | – | – |
| 2025-10-09T05:00Z | 2.47 / 11.17 / 122.03 | 2.43 / 11.17 / 124.1 | 0.47 / 3.23 / 22.45 | – | – |

## Datasett: MyWave_wam800_c1WAVE00.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800n/MyWave_wam800_c1WAVE00.nc
- Tid: 2025-10-07 18:00:00 → 2025-10-10 18:00:00 (73 steg)
- Rutenett: [952, 228] punkter, lat [66.12361145019531, 72.00888061523438], lon [9.490080833435059, 29.698686599731445], våte punkter 110304
- Globale attributter: {"title": "MyWaveWam 800m NordNorge", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Wed Oct  8 04:00:39 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c1WAVE00.nc"}
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

- grotfjord: dekkes også her (0.41 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
- tromvik: dekkes også her (0.41 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
- ersfjordstranda: dekkes også her (0.21 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
- russelv: dekkes også her (0.29 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
- lenangsoyra: dekkes også her (0.35 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
- steinkrossa: dekkes også her (0.25 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
- unstad: dekkes også her (0.46 km fra ønsket punkt) - allerede rapportert fra MyWave_wam800_c1WAVE12.nc
## Datasett: MyWave_wam800_c0WAVE12.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800f/MyWave_wam800_c0WAVE12.nc
- Tid: 2025-10-07 06:00:00 → 2025-10-10 06:00:00 (73 steg)
- Rutenett: [199, 381] punkter, lat [69.34889221191406, 71.74052429199219], lon [25.621408462524414, 33.65534973144531], våte punkter 43960
- Globale attributter: {"title": "MyWaveWam 800m Finnmark", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Tue Oct  7 15:57:50 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c0WAVE12.nc\nThu Feb 11 15:38:19 2016: ncatted -O -a grid_mapping,depth,c,c,projection_3 TRUEcoordDepthc0.nc", "summary": "The WAM-model is a third generation wave model. The model runs for any given regional or global grid with a prescribed topographic dataset. It has the potential to provide environmental information for
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

## Datasett: MyWave_wam800_c0WAVE00.nc
- URL: https://thredds.met.no/thredds/dodsC/fou-hi/mywavewam800f/MyWave_wam800_c0WAVE00.nc
- Tid: 2025-10-07 18:00:00 → 2025-10-10 18:00:00 (73 steg)
- Rutenett: [199, 381] punkter, lat [69.34889221191406, 71.74052429199219], lon [25.621408462524414, 33.65534973144531], våte punkter 43960
- Globale attributter: {"title": "MyWaveWam 800m Finnmark", "institution": "Norwegian Meteorological Institute", "source": "WAM wave model version cycle 4.7.0", "comment": "Original grid rotated", "history": "Wed Oct  8 03:59:44 2025: ncks -A -v forecast_reference_time WIND_INPUT.DAT MyWave_wam800_c0WAVE00.nc\nThu Feb 11 15:38:19 2016: ncatted -O -a grid_mapping,depth,c,c,projection_3 TRUEcoordDepthc0.nc"}
- Roller (gjenkjent automatisk): {"total_dir": "thq", "total_hs": "hs", "total_tp": "tp", "sea_hs": "hs_sea", "sea_tp": "tp_sea", "sea_dir": "thq_sea", "swell_hs": "hs_swell", "swell_tp": "tp_swell", "swell_dir": "thq_swell"}
- Variabler (navn, dims, standard_name/long_name/units):
  - `ff` ['time', 'rlat', 'rlon'] wind_speed / Wind speed / m s-1
  - `dd` ['time', 'rlat', 'rlon'] wind_to_direction / Wind direction / degree
  - `FV` ['time', 'rlat', 'rlon'] FV / friction velocity / m s-1
  - `DC` ['time', 'rlat', 'rlon'] DC / drag coefficient / 
  - `hs` ['time', 'rlat', 'rlon'] sea_surface_wave_significant_height / Total significant wave height / m
  - `tp` ['time', 'rlat', 'rlon'] sea_surface_wave_period_at_variance_spectral_density_maximum / Total peak period / s
  - `tmp` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Total mean period / s
  - `tm1` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Total m1-period / s
  - `tm2` ['time', 'rlat', 'rlon'] sea_surface_wave_mean_period_from_variance_spectral_density_second_frequency_moment / Total m2-period / s
  - `thq` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction / Total mean wave direction / degree
  - `hs_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_significant_height / Sea significant wave height / m
  - `tp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_peak_period_from_variance_spectral_density / Sea peak period / s
  - `tmp_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Sea mean period / s
  - `tm1_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Sea m1-period / s
  - `thq_sea` ['time', 'rlat', 'rlon'] sea_surface_wind_wave_to_direction / Sea mean wave direction / degree
  - `hs_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_significant_height / Swell significant wave height / m
  - `tp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_peak_period_from_variance_spectral_density / Swell peak period / s
  - `tmp_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_inverse_frequency_moment / Swell mean period / s
  - `tm1_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_mean_period_from_variance_spectral_density_first_frequency_moment / Swell m1-period / s
  - `thq_swell` ['time', 'rlat', 'rlon'] sea_surface_swell_wave_to_direction / Swell mean wave direction / degree
  - `mHs` ['time', 'rlat', 'rlon'] expected_maximum_wave_height / expected maximum wave height / m
  - `mwp` ['time', 'rlat', 'rlon'] expected_wave_period / expected wave period / s
  - `fpI` ['time', 'rlat', 'rlon'] interpolated_peak_frequency / interpolated peak frequency / 1/s
  - `Pdir` ['time', 'rlat', 'rlon'] sea_surface_wave_to_direction_at_variance_spectral_density_maximu / peak direction / degree
  - `fshs` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_significant_height / first swell significant wave height / m
  - `fstm1` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_mean_period / first swell mean period / s
  - `fsdir` ['time', 'rlat', 'rlon'] sea_surface_primary_swell_wave_to_direction / first swell direction / degree
  - `sshs` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_significant_height / second swell significant wave height / m
  - `sstm1` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_mean_period / second swell mean period / s
  - `ssdir` ['time', 'rlat', 'rlon'] sea_surface_secondary_swell_wave_to_direction / second swell direction / degree
  - `tshs` ['time', 'rlat', 'rlon'] third swell significant wave height / third swell significant wave height / m
  - `tstm1` ['time', 'rlat', 'rlon'] third swell mean period / third swell mean period / m/s
  - `tsdir` ['time', 'rlat', 'rlon'] third swell direction / third swell direction / degree
  - `utrs` ['time', 'rlat', 'rlon'] DEEP_WATER_X_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / x-comp Stokes drift transport / m^2/s
  - `sdx` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_x_velocity / x-comp. Stokes drift / m/s
  - `sdy` ['time', 'rlat', 'rlon'] sea_surface_wave_stokes_drift_y_velocity / y-comp. Stokes drift / m/s
  - `phioc` ['time', 'rlat', 'rlon'] energy flux to ocean / energy flux to ocean / W*m^-2
  - `phiaw` ['time', 'rlat', 'rlon'] energy flux from wind to waves / energy flux from wind to waves / W*m^-2
  - `tauocx` ['time', 'rlat', 'rlon'] x-comp. momentum flux into ocean / x-comp. momentum flux into ocean / N*m^-2
  - `tauocy` ['time', 'rlat', 'rlon'] y-comp. momentum flux into ocean / y-comp. momentum flux into ocean / N*m^-2
  - `phibot` ['time', 'rlat', 'rlon'] energy flux from waves to bottom / energy flux from waves to bottom / W*m^-2
  - `taubot_x` ['time', 'rlat', 'rlon'] x-comp. momentum flux from waves into bottom / x-comp. momentum flux from waves into bottom / N*m^-2
  - `taubot_y` ['time', 'rlat', 'rlon'] y-comp. momentum flux from waves into bottom / y-comp. momentum flux from waves into bottom / Nm^-2
  - `vtrs` ['time', 'rlat', 'rlon'] DEEP_WATER_Y_COMPONENT_OF_STOKES_DRIFT_TRANSPORT / y-comp Stokes drift transport / m^2/s
  - `Hmax_N` ['time', 'rlat', 'rlon'] sea_surface_wave_maximum_height / Maximum crest trough wave height (Hc,max) / m
  - `hmax_st` ['time', 'rlat', 'rlon'] HMAX (SPACE-TIME (STQD)) / maximum wave height - space-time (stqd) / m
  - `depth` ['rlat', 'rlon'] depth /  / m
  - `latitude` ['rlat', 'rlon'] latitude /  / degrees_north
  - `longitude` ['rlat', 'rlon'] longitude /  / degrees_east

## Spots uten dekning i noe datasett

ingen - alle dekket

## Neste steg (ROADMAP J.4-J.6)

Sammenlign kildene mot de faste observasjonene (krever arkivdata for 24.-28.09 og 05.10.2026 - sjekk om thredds har arkiv), og foreslå bruk (J.5) i STATUS.md. Ingenting kobles inn uten Theodors ja.
