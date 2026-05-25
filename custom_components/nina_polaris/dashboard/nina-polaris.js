/**
 * NINA Polaris — Lovelace Dashboard Strategy
 *
 * Auto-generates a dashboard view per NINA instance by reading the
 * entity registry. Users add it to a dashboard with:
 *
 *   strategy:
 *     type: custom:nina-polaris
 *
 * Optional config:
 *   show_chips: true | false (default true)
 *   show_charts: true | false (default true) — needs apexcharts-card
 *   use_mushroom: true | false (default true) — needs Mushroom cards
 *   instance: "<entry_id>"  — limit to a single instance
 */

const DOMAIN = "nina_polaris";

class NinaPolarisDashboardStrategy extends HTMLElement {
  static async generate(config, hass) {
    const cfg = config || {};
    const useMushroom = cfg.use_mushroom !== false;
    const showCharts = cfg.show_charts !== false;

    const instances = collectInstances(hass, cfg.instance);
    if (instances.length === 0) {
      return {
        title: "NINA Polaris",
        views: [
          {
            title: "NINA",
            cards: [
              {
                type: "markdown",
                content:
                  "### NINA Polaris\n\nNo NINA Polaris instance detected. " +
                  "Make sure the integration is configured in **Settings → Devices & services**.",
              },
            ],
          },
        ],
      };
    }

    return {
      title: "NINA Polaris",
      views: instances.map((inst) =>
        buildView(inst, { useMushroom, showCharts }),
      ),
    };
  }
}

class NinaPolarisViewStrategy extends HTMLElement {
  static async generate(config, hass) {
    const cfg = config || {};
    const useMushroom = cfg.use_mushroom !== false;
    const showCharts = cfg.show_charts !== false;
    const inst = collectInstances(hass, cfg.instance)[0];
    if (!inst) {
      return {
        cards: [
          {
            type: "markdown",
            content: "No NINA Polaris instance detected.",
          },
        ],
      };
    }
    const view = buildView(inst, { useMushroom, showCharts });
    return { cards: view.cards };
  }
}

// ---------------------------------------------------------------------------

function collectInstances(hass, onlyEntryId) {
  // Group our entities by device_id (available in the frontend display entry).
  // config_entry_id is NOT present in the display-format entity registry,
  // so we resolve it via the device registry instead.
  const byDevice = new Map();
  for (const entity of Object.values(hass.entities || {})) {
    if (!entity || entity.platform !== DOMAIN) continue;
    const deviceId = entity.device_id;
    if (!deviceId) continue;
    if (!byDevice.has(deviceId)) byDevice.set(deviceId, []);
    byDevice.get(deviceId).push(entity.entity_id);
  }

  const results = [];
  for (const [deviceId, entityIds] of byDevice) {
    const device = (hass.devices || {})[deviceId];
    const entryId = device?.config_entries?.[0] || deviceId;
    if (onlyEntryId && entryId !== onlyEntryId) continue;
    results.push({
      entry_id: entryId,
      title: device?.name_by_user || device?.name || "NINA",
      entities: indexByKey(entityIds),
    });
  }
  return results;
}


/**
 * Index entity_ids by their NINA "key" suffix.
 * Our unique_ids are `<entry>_<key>` and HA derives entity_ids the same way:
 *   sensor.nina_camera_temperature, binary_sensor.nina_camera_connected, ...
 * So we strip the leading `<domain>.<prefix_>` to get the key.
 */
function indexByKey(entityIds) {
  const map = {};
  for (const eid of entityIds) {
    const [domain, object] = eid.split(".");
    // Strip the "nina[_2]_" instance prefix so we land on the bare key.
    // Examples : nina_camera_temperature, nina_2_camera_temperature
    const stripped = object.replace(/^nina(?:_\d+)?_/, "");
    map[`${domain}.${stripped}`] = eid;
    // Also index without the platform domain so callers can ask either way.
    if (!(stripped in map)) map[stripped] = eid;
  }
  return map;
}

function eid(inst, key) {
  return inst.entities[key];
}

// ---------------------------------------------------------------------------

function buildView(inst, opts) {
  const cards = [];

  // Hero — last image
  const camera = eid(inst, "camera.latest_image");
  if (camera) {
    cards.push({
      type: "picture-entity",
      entity: camera,
      camera_view: "auto",
      show_state: false,
      show_name: false,
      aspect_ratio: "3:2",
    });
  }

  // Equipment status chips (Mushroom)
  if (opts.useMushroom) {
    const chips = buildEquipmentChips(inst);
    if (chips.length > 0) {
      cards.push({ type: "custom:mushroom-chips-card", chips });
    }
  }

  // Sequence + actions
  cards.push(buildSequenceCard(inst, opts));

  // Mount section
  const mountCard = buildMountCard(inst, opts);
  if (mountCard) cards.push(mountCard);

  // Camera section
  const cameraCard = buildCameraCard(inst, opts);
  if (cameraCard) cards.push(cameraCard);

  // Guider chart
  if (opts.showCharts) {
    const guiderCard = buildGuiderChart(inst);
    if (guiderCard) cards.push(guiderCard);
  }

  // Focuser
  const focuserCard = buildFocuserCard(inst, opts);
  if (focuserCard) cards.push(focuserCard);

  // Weather / SQM
  const weatherCard = buildWeatherCard(inst, opts);
  if (weatherCard) cards.push(weatherCard);

  return {
    title: inst.title,
    path: `nina-${inst.entry_id.slice(0, 8)}`,
    icon: "mdi:telescope",
    cards,
  };
}

function buildEquipmentChips(inst) {
  const list = [
    ["binary_sensor.camera_connected", "mdi:camera", "Camera"],
    ["binary_sensor.mount_connected", "mdi:telescope", "Mount"],
    ["binary_sensor.guider_connected", "mdi:target", "Guider"],
    ["binary_sensor.focuser_connected", "mdi:image-filter-center-focus", "Focuser"],
    ["binary_sensor.filterwheel_connected", "mdi:circle-multiple", "FW"],
    ["binary_sensor.rotator_connected", "mdi:rotate-left", "Rotator"],
    ["binary_sensor.dome_connected", "mdi:dome-light", "Dome"],
    ["binary_sensor.weather_connected", "mdi:weather-partly-cloudy", "Weather"],
    ["binary_sensor.safety_monitor_connected", "mdi:shield-check", "Safety"],
  ];
  const chips = [];
  for (const [key, icon, label] of list) {
    const entity = eid(inst, key);
    if (!entity) continue;
    chips.push({
      type: "entity",
      entity,
      icon,
      content_info: "none",
      tap_action: { action: "more-info" },
      icon_color: `\${state == 'on' ? 'green' : 'disabled'}`,
    });
    void label;
  }
  return chips;
}

function buildSequenceCard(inst, opts) {
  const target = eid(inst, "sensor.sequence_current_target");
  const running = eid(inst, "binary_sensor.sequence_running");
  const start = eid(inst, "button.start_sequence");
  const stop = eid(inst, "button.stop_sequence");
  const af = eid(inst, "button.run_autofocus");
  const ps = eid(inst, "button.plate_solve");

  const entities = [];
  if (target) entities.push({ entity: target, name: "Current target" });
  if (running) entities.push({ entity: running, name: "Sequence running" });

  const buttons = [start, stop, af, ps].filter(Boolean).map((e) => ({
    type: "custom:mushroom-entity-card",
    entity: e,
    tap_action: { action: "toggle" },
    icon_color: "blue",
    fill_container: true,
  }));

  const cards = [];
  if (entities.length > 0) cards.push({ type: "entities", title: "Sequence", entities });
  if (buttons.length > 0) {
    cards.push({
      type: "horizontal-stack",
      cards: buttons,
    });
  }
  return cards.length === 1 ? cards[0] : { type: "vertical-stack", cards };
}

function buildMountCard(inst, opts) {
  const entries = [
    ["sensor.mount_ra", "RA"],
    ["sensor.mount_dec", "Dec"],
    ["sensor.mount_altitude", "Altitude"],
    ["sensor.mount_azimuth", "Azimuth"],
    ["sensor.time_to_meridian_flip", "Meridian flip in"],
    ["binary_sensor.mount_tracking", "Tracking"],
    ["binary_sensor.mount_slewing", "Slewing"],
    ["binary_sensor.mount_parked", "Parked"],
    ["switch.mount_tracking", "Tracking control"],
    ["button.park_mount", "Park"],
    ["button.unpark_mount", "Unpark"],
  ]
    .map(([key, name]) => {
      const e = eid(inst, key);
      return e ? { entity: e, name } : null;
    })
    .filter(Boolean);
  if (entries.length === 0) return null;
  return { type: "entities", title: "Mount", entities: entries };
}

function buildCameraCard(inst, opts) {
  const entries = [
    ["sensor.camera_temperature", "Temperature"],
    ["sensor.camera_cooler_power", "Cooler power"],
    ["binary_sensor.camera_exposing", "Exposing"],
    ["binary_sensor.camera_cooler_on", "Cooler"],
    ["switch.camera_cooler", "Cooler control"],
  ]
    .map(([key, name]) => {
      const e = eid(inst, key);
      return e ? { entity: e, name } : null;
    })
    .filter(Boolean);
  if (entries.length === 0) return null;
  return { type: "entities", title: "Camera", entities: entries };
}

function buildGuiderChart(inst) {
  const ra = eid(inst, "sensor.guider_ra_distance");
  const dec = eid(inst, "sensor.guider_dec_distance");
  if (!ra && !dec) return null;
  const series = [];
  if (ra) series.push({ entity: ra, name: "RA error", stroke_width: 2 });
  if (dec) series.push({ entity: dec, name: "Dec error", stroke_width: 2 });
  return {
    type: "custom:apexcharts-card",
    header: { title: "Guider error", show: true, show_states: true },
    graph_span: "30min",
    span: { end: "minute" },
    apex_config: {
      chart: { height: 220 },
      yaxis: { decimalsInFloat: 2, title: { text: "px" } },
    },
    series,
  };
}

function buildFocuserCard(inst, opts) {
  const entries = [
    ["sensor.focuser_position", "Position"],
    ["sensor.focuser_temperature", "Temperature"],
    ["button.run_autofocus", "Run autofocus"],
  ]
    .map(([key, name]) => {
      const e = eid(inst, key);
      return e ? { entity: e, name } : null;
    })
    .filter(Boolean);
  if (entries.length === 0) return null;
  return { type: "entities", title: "Focuser", entities: entries };
}

function buildWeatherCard(inst, opts) {
  const entries = [
    ["sensor.weather_temperature", "Temperature"],
    ["sensor.weather_humidity", "Humidity"],
    ["sensor.weather_dew_point", "Dew point"],
    ["sensor.weather_wind_speed", "Wind"],
    ["sensor.weather_pressure", "Pressure"],
    ["sensor.sky_quality_sqm", "SQM"],
    ["sensor.sky_temperature", "Sky temp"],
    ["binary_sensor.observatory_safe", "Safe"],
  ]
    .map(([key, name]) => {
      const e = eid(inst, key);
      return e ? { entity: e, name } : null;
    })
    .filter(Boolean);
  if (entries.length === 0) return null;
  return { type: "entities", title: "Weather & SQM", entities: entries };
}

// ---------------------------------------------------------------------------

customElements.define(
  "ll-strategy-dashboard-nina-polaris",
  NinaPolarisDashboardStrategy,
);
customElements.define(
  "ll-strategy-view-nina-polaris",
  NinaPolarisViewStrategy,
);

// Older HA frontends look for these names too.
customElements.define("ll-strategy-nina-polaris", NinaPolarisViewStrategy);
