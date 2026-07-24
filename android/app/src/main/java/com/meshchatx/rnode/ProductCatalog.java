package com.meshchatx.rnode;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Loads RNode ESP flash product catalog from assets/rnode_products.json. */
public final class ProductCatalog {
    public static final class Model {
        public final int id;
        public final String name;
        public final Integer mappedId;
        public final Map<String, String> flashFiles;
        public final String flashSize;
        public final String firmwareFilename;

        Model(
            int id,
            String name,
            Integer mappedId,
            Map<String, String> flashFiles,
            String flashSize,
            String firmwareFilename
        ) {
            this.id = id;
            this.name = name;
            this.mappedId = mappedId;
            this.flashFiles = flashFiles;
            this.flashSize = flashSize;
            this.firmwareFilename = firmwareFilename;
        }

        @Override
        public String toString() {
            return name;
        }
    }

    public static final class Product {
        public final String name;
        public final int id;
        public final int platform;
        public final String firmwareFilename;
        public final Map<String, String> flashFiles;
        public final String flashSize;
        public final List<Model> models;

        Product(
            String name,
            int id,
            int platform,
            String firmwareFilename,
            Map<String, String> flashFiles,
            String flashSize,
            List<Model> models
        ) {
            this.name = name;
            this.id = id;
            this.platform = platform;
            this.firmwareFilename = firmwareFilename;
            this.flashFiles = flashFiles;
            this.flashSize = flashSize;
            this.models = models;
        }

        @Override
        public String toString() {
            return name;
        }

        public Map<String, String> resolveFlashFiles(Model model) {
            if (model != null && model.flashFiles != null && !model.flashFiles.isEmpty()) {
                return model.flashFiles;
            }
            return flashFiles;
        }

        public String resolveFirmwareFilename(Model model) {
            if (model != null && model.firmwareFilename != null && !model.firmwareFilename.isEmpty()) {
                return model.firmwareFilename;
            }
            return firmwareFilename;
        }
    }

    private final List<Product> products;

    private ProductCatalog(List<Product> products) {
        this.products = products;
    }

    public static ProductCatalog empty() {
        return new ProductCatalog(new ArrayList<>());
    }

    public List<Product> products() {
        return products;
    }

    public static ProductCatalog load(Context context) throws Exception {
        String json;
        try (InputStream in = context.getAssets().open("rnode_products.json");
             BufferedReader reader =
                 new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            json = sb.toString();
        }
        JSONArray arr = new JSONArray(json);
        List<Product> products = new ArrayList<>();
        for (int i = 0; i < arr.length(); i++) {
            JSONObject obj = arr.getJSONObject(i);
            Map<String, String> flashFiles = readFlashFiles(obj.optJSONObject("flash_config"));
            String flashSize = readFlashSize(obj.optJSONObject("flash_config"));
            List<Model> models = new ArrayList<>();
            JSONArray modelsArr = obj.optJSONArray("models");
            if (modelsArr != null) {
                for (int j = 0; j < modelsArr.length(); j++) {
                    JSONObject m = modelsArr.getJSONObject(j);
                    Integer mapped = m.has("mapped_id") && !m.isNull("mapped_id")
                        ? m.getInt("mapped_id")
                        : null;
                    Map<String, String> modelFlash = readFlashFiles(m.optJSONObject("flash_config"));
                    String modelSize = readFlashSize(m.optJSONObject("flash_config"));
                    models.add(
                        new Model(
                            m.getInt("id"),
                            m.getString("name"),
                            mapped,
                            modelFlash,
                            modelSize,
                            m.optString("firmware_filename", null)
                        )
                    );
                }
            }
            products.add(
                new Product(
                    obj.getString("name"),
                    obj.getInt("id"),
                    obj.getInt("platform"),
                    obj.optString("firmware_filename", ""),
                    flashFiles,
                    flashSize,
                    models
                )
            );
        }
        return new ProductCatalog(products);
    }

    private static Map<String, String> readFlashFiles(JSONObject flashConfig) {
        Map<String, String> map = new LinkedHashMap<>();
        if (flashConfig == null) {
            return map;
        }
        JSONObject files = flashConfig.optJSONObject("flash_files");
        if (files == null) {
            return map;
        }
        Iterator<String> keys = files.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            map.put(key, files.optString(key, ""));
        }
        return map;
    }

    private static String readFlashSize(JSONObject flashConfig) {
        if (flashConfig == null) {
            return "4MB";
        }
        return flashConfig.optString("flash_size", "4MB");
    }
}
