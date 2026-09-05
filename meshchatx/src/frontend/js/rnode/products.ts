import ROM from "./ROM.js";

export default [
    {
        name: "Heltec LoRa32 v2",
        id: ROM.PRODUCT_H32_V2,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_C4,
                name: "433 MHz",
            },
            {
                id: ROM.MODEL_C9,
                name: "868 MHz / 915 MHz / 923 MHz",
            },
        ],
        firmware_filename: "rnode_firmware_heltec32v2.zip",
        flash_config: {
            flash_size: "8MB",
            flash_files: {
                "0xe000": "rnode_firmware_heltec32v2.boot_app0",
                "0x1000": "rnode_firmware_heltec32v2.bootloader",
                "0x10000": "rnode_firmware_heltec32v2.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_heltec32v2.partitions",
            },
        },
    },
    {
        name: "Heltec LoRa32 v3",
        id: ROM.PRODUCT_H32_V3,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_C5,
                name: "433 MHz",
            },
            {
                id: ROM.MODEL_CA,
                name: "868 MHz / 915 MHz / 923 MHz",
            },
        ],
        firmware_filename: "rnode_firmware_heltec32v3.zip",
        flash_config: {
            flash_size: "8MB",
            flash_files: {
                "0xe000": "rnode_firmware_heltec32v3.boot_app0",
                "0x0": "rnode_firmware_heltec32v3.bootloader",
                "0x10000": "rnode_firmware_heltec32v3.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_heltec32v3.partitions",
            },
        },
    },
    {
        name: "Heltec LoRa32 v4",
        id: ROM.PRODUCT_H32_V4,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_C8,
                name: "868 MHz / 915 MHz / 923 MHz with PA",
            },
        ],
        firmware_filename: "rnode_firmware_heltec32v4pa.zip",
        flash_config: {
            flash_size: "16MB",
            flash_files: {
                "0xe000": "rnode_firmware_heltec32v4pa.boot_app0",
                "0x0": "rnode_firmware_heltec32v4pa.bootloader",
                "0x10000": "rnode_firmware_heltec32v4pa.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_heltec32v4pa.partitions",
            },
        },
    },
    {
        name: "Heltec T114",
        id: ROM.PRODUCT_HELTEC_T114,
        platform: ROM.PLATFORM_NRF52,
        models: [
            {
                id: ROM.MODEL_C6,
                name: "470-510 MHz (HT-n5262-LF)",
            },
            {
                id: ROM.MODEL_C7,
                name: "863-928 MHz (HT-n5262-HF)",
            },
        ],
        firmware_filename: "rnode_firmware_heltec_t114.zip",
    },
    {
        name: "LilyGO LoRa32 v1.0",
        id: ROM.PRODUCT_T32_10,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_BA,
                name: "433 MHz",
            },
            {
                id: ROM.MODEL_BB,
                name: "868 MHz / 915 MHz / 923 MHz",
            },
        ],
        firmware_filename: "rnode_firmware_lora32v10.zip",
        flash_config: {
            flash_size: "4MB",
            flash_files: {
                "0xe000": "rnode_firmware_lora32v10.boot_app0",
                "0x1000": "rnode_firmware_lora32v10.bootloader",
                "0x10000": "rnode_firmware_lora32v10.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_lora32v10.partitions",
            },
        },
    },
    {
        name: "LilyGO LoRa32 v2.0",
        id: ROM.PRODUCT_T32_20,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_B3,
                name: "433 MHz",
            },
            {
                id: ROM.MODEL_B8,
                name: "868 MHz / 915 MHz / 923 MHz",
            },
        ],
        firmware_filename: "rnode_firmware_lora32v20.zip",
        flash_config: {
            flash_size: "4MB",
            flash_files: {
                "0xe000": "rnode_firmware_lora32v20.boot_app0",
                "0x1000": "rnode_firmware_lora32v20.bootloader",
                "0x10000": "rnode_firmware_lora32v20.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_lora32v20.partitions",
            },
        },
    },
    {
        name: "LilyGO LoRa32 v2.1",
        id: ROM.PRODUCT_T32_21,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_B4,
                name: "433 MHz",
                firmware_filename: "rnode_firmware_lora32v21.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_lora32v21.boot_app0",
                        "0x1000": "rnode_firmware_lora32v21.bootloader",
                        "0x10000": "rnode_firmware_lora32v21.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_lora32v21.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_B9,
                name: "868/915/923 MHz",
                firmware_filename: "rnode_firmware_lora32v21.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_lora32v21.boot_app0",
                        "0x1000": "rnode_firmware_lora32v21.bootloader",
                        "0x10000": "rnode_firmware_lora32v21.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_lora32v21.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_B4_TCXO,
                mapped_id: ROM.MODEL_B4,
                name: "433 MHz, with TCXO",
                firmware_filename: "rnode_firmware_lora32v21_tcxo.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_lora32v21_tcxo.boot_app0",
                        "0x1000": "rnode_firmware_lora32v21_tcxo.bootloader",
                        "0x10000": "rnode_firmware_lora32v21_tcxo.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_lora32v21_tcxo.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_B9_TCXO,
                mapped_id: ROM.MODEL_B9,
                name: "868/915/923 MHz, with TCXO",
                firmware_filename: "rnode_firmware_lora32v21_tcxo.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_lora32v21_tcxo.boot_app0",
                        "0x1000": "rnode_firmware_lora32v21_tcxo.bootloader",
                        "0x10000": "rnode_firmware_lora32v21_tcxo.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_lora32v21_tcxo.partitions",
                    },
                },
            },
        ],
    },
    {
        name: "LilyGO LoRa T3S3",
        id: ROM.PRODUCT_RNODE,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_A5,
                name: "433 MHz (with SX1278 chip)",
                firmware_filename: "rnode_firmware_t3s3_sx127x.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3_sx127x.boot_app0",
                        "0x0": "rnode_firmware_t3s3_sx127x.bootloader",
                        "0x10000": "rnode_firmware_t3s3_sx127x.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3_sx127x.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_AA,
                name: "868/915/923 MHz (with SX1276 chip)",
                firmware_filename: "rnode_firmware_t3s3_sx127x.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3_sx127x.boot_app0",
                        "0x0": "rnode_firmware_t3s3_sx127x.bootloader",
                        "0x10000": "rnode_firmware_t3s3_sx127x.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3_sx127x.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_A1,
                name: "433 MHz (with SX1268 chip)",
                firmware_filename: "rnode_firmware_t3s3.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3.boot_app0",
                        "0x0": "rnode_firmware_t3s3.bootloader",
                        "0x10000": "rnode_firmware_t3s3.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_A6,
                name: "868/915/923 MHz (with SX1262 chip)",
                firmware_filename: "rnode_firmware_t3s3.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3.boot_app0",
                        "0x0": "rnode_firmware_t3s3.bootloader",
                        "0x10000": "rnode_firmware_t3s3.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_AC,
                name: "2.4 GHz (with SX1280 chip)",
                firmware_filename: "rnode_firmware_t3s3_sx1280_pa.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3_sx1280_pa.boot_app0",
                        "0x0": "rnode_firmware_t3s3_sx1280_pa.bootloader",
                        "0x10000": "rnode_firmware_t3s3_sx1280_pa.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3_sx1280_pa.partitions",
                    },
                },
            },
        ],
    },
    {
        name: "LilyGO T-Beam",
        id: ROM.PRODUCT_TBEAM,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_E4,
                name: "433 MHz (with SX1278 chip)",
                firmware_filename: "rnode_firmware_tbeam.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_tbeam.boot_app0",
                        "0x1000": "rnode_firmware_tbeam.bootloader",
                        "0x10000": "rnode_firmware_tbeam.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_tbeam.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_E9,
                name: "868/915/923 MHz (with SX1276 chip)",
                firmware_filename: "rnode_firmware_tbeam.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_tbeam.boot_app0",
                        "0x1000": "rnode_firmware_tbeam.bootloader",
                        "0x10000": "rnode_firmware_tbeam.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_tbeam.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_E3,
                name: "433 MHz (with SX1268 chip)",
                firmware_filename: "rnode_firmware_tbeam_sx1262.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_tbeam_sx1262.boot_app0",
                        "0x1000": "rnode_firmware_tbeam_sx1262.bootloader",
                        "0x10000": "rnode_firmware_tbeam_sx1262.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_tbeam_sx1262.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_E8,
                name: "868/915/923 MHz (with SX1262 chip)",
                firmware_filename: "rnode_firmware_tbeam_sx1262.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_tbeam_sx1262.boot_app0",
                        "0x1000": "rnode_firmware_tbeam_sx1262.bootloader",
                        "0x10000": "rnode_firmware_tbeam_sx1262.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_tbeam_sx1262.partitions",
                    },
                },
            },
        ],
    },
    {
        name: "LilyGO T-Beam Supreme",
        id: ROM.PRODUCT_TBEAM_S_V1,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_DB,
                name: "433 MHz (with SX1268 chip)",
            },
            {
                id: ROM.MODEL_DC,
                name: "868/915/923 MHz (with SX1262 chip)",
            },
        ],
        firmware_filename: "rnode_firmware_tbeam_supreme.zip",
        flash_config: {
            flash_size: "4MB",
            flash_files: {
                "0xe000": "rnode_firmware_tbeam_supreme.boot_app0",
                "0x0": "rnode_firmware_tbeam_supreme.bootloader",
                "0x10000": "rnode_firmware_tbeam_supreme.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_tbeam_supreme.partitions",
            },
        },
    },
    {
        name: "LilyGO T-Deck",
        id: ROM.PRODUCT_TDECK,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_D4,
                name: "433 MHz (with SX1268 chip)",
            },
            {
                id: ROM.MODEL_D9,
                name: "868/915/923 MHz (with SX1262 chip)",
            },
        ],
        firmware_filename: "rnode_firmware_tdeck.zip",
        flash_config: {
            flash_size: "4MB",
            flash_files: {
                "0xe000": "rnode_firmware_tdeck.boot_app0",
                "0x0": "rnode_firmware_tdeck.bootloader",
                "0x10000": "rnode_firmware_tdeck.bin",
                "0x210000": "console_image.bin",
                "0x8000": "rnode_firmware_tdeck.partitions",
            },
        },
    },
    {
        name: "LilyGO T-Echo",
        id: ROM.PRODUCT_TECHO,
        platform: ROM.PLATFORM_NRF52,
        models: [
            {
                id: ROM.MODEL_16,
                name: "433 MHz",
            },
            {
                id: ROM.MODEL_17,
                name: "868 MHz / 915 MHz / 923 MHz",
            },
        ],
        firmware_filename: "rnode_firmware_techo.zip",
    },
    {
        name: "RAK4631",
        id: ROM.PRODUCT_RAK4631,
        platform: ROM.PLATFORM_NRF52,
        models: [
            {
                id: ROM.MODEL_11,
                name: "433 MHz",
            },
            {
                id: ROM.MODEL_12,
                name: "868 MHz / 915 MHz / 923 MHz",
            },
        ],
        firmware_filename: "rnode_firmware_rak4631.zip",
    },
    {
        name: "RNode",
        id: ROM.PRODUCT_RNODE,
        platform: ROM.PLATFORM_ESP32,
        models: [
            {
                id: ROM.MODEL_A2,
                name: "Handheld v2.1 RNode, 410 - 525 MHz",
                firmware_filename: "rnode_firmware_ng21.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_ng21.boot_app0",
                        "0x1000": "rnode_firmware_ng21.bootloader",
                        "0x10000": "rnode_firmware_ng21.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_ng21.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_A7,
                name: "Handheld v2.1 RNode, 820 - 1020 MHz",
                firmware_filename: "rnode_firmware_ng21.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_ng21.boot_app0",
                        "0x1000": "rnode_firmware_ng21.bootloader",
                        "0x10000": "rnode_firmware_ng21.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_ng21.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_A1,
                name: "Prototype v2.2 RNode, 410 - 525 MHz",
                firmware_filename: "rnode_firmware_t3s3.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3.boot_app0",
                        "0x0": "rnode_firmware_t3s3.bootloader",
                        "0x10000": "rnode_firmware_t3s3.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3.partitions",
                    },
                },
            },
            {
                id: ROM.MODEL_A6,
                name: "Prototype v2.2 RNode, 820 - 1020 MHz",
                firmware_filename: "rnode_firmware_t3s3.zip",
                flash_config: {
                    flash_size: "4MB",
                    flash_files: {
                        "0xe000": "rnode_firmware_t3s3.boot_app0",
                        "0x0": "rnode_firmware_t3s3.bootloader",
                        "0x10000": "rnode_firmware_t3s3.bin",
                        "0x210000": "console_image.bin",
                        "0x8000": "rnode_firmware_t3s3.partitions",
                    },
                },
            },
        ],
    },
];
