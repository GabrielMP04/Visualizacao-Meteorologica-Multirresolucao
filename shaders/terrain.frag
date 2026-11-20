#version 330 core

in vec3 v_world_position;
in vec3 v_normal;
in float v_temperature;
in vec2 v_texture_uv;

uniform sampler2D u_terrain_texture;
uniform bool u_has_texture;
uniform float u_temperature_opacity;

uniform vec3 u_camera_position;
uniform vec3 u_light_direction;
uniform float u_temperature_min;
uniform float u_temperature_max;
uniform float u_fog_start;
uniform float u_fog_end;
uniform vec3 u_fog_color;

uniform bool u_state;
uniform sampler2D u_clip;
uniform sampler2D u_field;
uniform vec4 u_grid_mapping;
out vec4 frag_color;

vec3 temperature_color(float value)
{
    float t = clamp((value - u_temperature_min) /
                    max(u_temperature_max - u_temperature_min, 0.001), 0.0, 1.0);
    vec3 cold = vec3(0.07, 0.18, 0.65);
    vec3 cool = vec3(0.00, 0.68, 0.90);
    vec3 mild = vec3(0.20, 0.75, 0.32);
    vec3 warm = vec3(1.00, 0.88, 0.08);
    vec3 hot = vec3(0.82, 0.08, 0.04);

    if (t < 0.25)
        return mix(cold, cool, smoothstep(0.0, 0.25, t));
    if (t < 0.50)
        return mix(cool, mild, smoothstep(0.25, 0.50, t));
    if (t < 0.75)
        return mix(mild, warm, smoothstep(0.50, 0.75, t));
    return mix(warm, hot, smoothstep(0.75, 1.0, t));
}

void main()
{
    vec2 uv = v_world_position.xz * u_grid_mapping.xy;
    if (u_state && texture(u_clip, uv).r < 0.5) discard;
    float value = v_temperature;
    bool available = true;
    if (u_state) {
        vec2 n = vec2(textureSize(u_field, 0));
        vec2 field_uv = (uv * (n - 1.0) + 0.5) / n;
        vec2 field = texture(u_field, field_uv).rg;
        available = field.g > 0.999;
        value = field.r / max(field.g, 0.00001);
    }
    vec3 normal = normalize(v_normal);
    vec3 light = normalize(u_light_direction);
    float diffuse = max(dot(normal, light), 0.0);
    float hemisphere = 0.5 + 0.5 * normal.y;
    float lighting = 0.30 + 0.55 * diffuse + 0.15 * hemisphere;

    vec3 base_color;
    if (u_has_texture) {
        base_color = texture(u_terrain_texture, v_texture_uv).rgb;
        if (u_temperature_opacity > 0.0 && available)
            base_color = mix(base_color, temperature_color(value), u_temperature_opacity);
    } else {
        base_color = temperature_color(value);
    }
    vec3 surface_color = base_color * lighting;

    float distance_to_camera = length(u_camera_position - v_world_position);
    float fog = smoothstep(u_fog_start, u_fog_end, distance_to_camera);
    vec3 final_color = mix(surface_color, u_fog_color, fog);
    frag_color = vec4(final_color, 1.0);
}

