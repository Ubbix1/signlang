{pkgs}: {
  deps = [
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
    pkgs.libGLU
    pkgs.libGL
    pkgs.postgresql
    pkgs.openssl
  ];
}
