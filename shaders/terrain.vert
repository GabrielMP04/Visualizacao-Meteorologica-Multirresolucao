#version 330 core

layout (location = 0) in vec3 a_position;
layout (location = 1) in vec3 a_normal;
layout (location = 2) in float a_temperature;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

out vec3 v_world_position;
out vec3 v_normal;
out float v_temperature;

void main()
{
    vec4 world_position = u_model * vec4(a_position, 1.0);
    v_world_position = world_position.xyz;
    v_normal = normalize(mat3(transpose(inverse(u_model))) * a_normal);
    v_temperature = a_temperature;
    gl_Position = u_projection * u_view * world_position;
}

