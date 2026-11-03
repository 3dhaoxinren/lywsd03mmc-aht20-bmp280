ENTRY(mod_detect)
SECTIONS {
  . = 0x16b00;
  .text : { *(.text*) *(.rodata*) }
  .data : { *(.data*) }
  .bss : { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
ASSERT(SIZEOF(.data) == 0, "Injected code must not need initialized RAM")
ASSERT(SIZEOF(.bss) == 0, "Injected code must reuse original sensor RAM only")
ASSERT(. < 0x20000 - 4, "Image must fit the 128 KiB OTA slot")
