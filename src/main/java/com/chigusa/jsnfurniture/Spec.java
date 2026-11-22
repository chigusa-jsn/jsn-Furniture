package com.chigusa.jsnfurniture;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * 家具1つ分の決まりごと。tools/gen.py が作る jsn_furniture_specs.json から読む。
 * kind: basic / seat / storage / lamp / curtain / display / furin / shishi / sink
 */
public record Spec(String id, String kind, String tab, boolean tall, boolean full, float seat, int rows, int light,
                   String sound, boolean wall, boolean hanging, String particles, String furin, boolean passable,
                   String tool, List<double[]> shape, List<double[]> openShape) {

    public boolean is(String k) {
        return kind.equals(k);
    }

    public record Bed(String id, String tab, boolean futon) {}

    public record Door(String id) {}

    public static final List<Spec> ALL = new ArrayList<>();
    public static final List<Bed> BEDS = new ArrayList<>();
    public static final List<Door> DOORS = new ArrayList<>();

    static {
        try (Reader r = new InputStreamReader(Spec.class.getResourceAsStream("/jsn_furniture_specs.json"), StandardCharsets.UTF_8)) {
            JsonObject root = JsonParser.parseReader(r).getAsJsonObject();
            for (JsonElement e : root.getAsJsonArray("furniture")) {
                JsonObject o = e.getAsJsonObject();
                ALL.add(new Spec(o.get("id").getAsString(), o.get("kind").getAsString(), o.get("tab").getAsString(),
                        o.get("tall").getAsBoolean(), o.get("full").getAsBoolean(), o.get("seat").getAsFloat(),
                        o.get("rows").getAsInt(), o.get("light").getAsInt(), o.get("sound").getAsString(),
                        o.get("wall").getAsBoolean(), o.get("hanging").getAsBoolean(), o.get("particles").getAsString(),
                        o.get("furin").getAsString(), o.get("passable").getAsBoolean(), o.get("tool").getAsString(),
                        boxes(o.get("shape")), boxes(o.get("open"))));
            }
            for (JsonElement e : root.getAsJsonArray("beds")) {
                JsonObject o = e.getAsJsonObject();
                BEDS.add(new Bed(o.get("id").getAsString(), o.get("tab").getAsString(), o.get("futon").getAsBoolean()));
            }
            for (JsonElement e : root.getAsJsonArray("doors")) {
                DOORS.add(new Door(e.getAsJsonObject().get("id").getAsString()));
            }
        } catch (Exception ex) {
            throw new IllegalStateException("jsn_furniture_specs.json を読めません", ex);
        }
    }

    private static List<double[]> boxes(JsonElement e) {
        List<double[]> out = new ArrayList<>();
        if (e == null || e.isJsonNull()) return out;
        for (JsonElement b : (JsonArray) e) {
            JsonArray a = b.getAsJsonArray();
            double[] d = new double[6];
            for (int i = 0; i < 6; i++) d[i] = a.get(i).getAsDouble();
            out.add(d);
        }
        return out;
    }
}
