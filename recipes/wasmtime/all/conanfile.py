from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration, ConanException
import os
import shutil

required_conan_version = ">=1.33.0"


class WasmtimeConan(ConanFile):
    name = 'wasmtime'
    homepage = 'https://github.com/bytecodealliance/wasmtime'
    license = 'Apache-2.0'
    url = 'https://github.com/conan-io/conan-center-index'
    description = "Standalone JIT-style runtime for WebAssembly, using Cranelift"
    topics = ("webassembly", "wasm", "wasi")
    settings = "os", "compiler", "arch"
    options = {
        "shared": [True, False],
        'fPIC': [True],
    }
    default_options = {
        'shared': False,
        'fPIC': True,
    }

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _minimum_cpp_standard(self):
        return 11

    @property
    def _minimum_compilers_version(self):
        return {
            "Visual Studio": "15",
            "apple-clang": "9.4",
            "clang": "3.3",
            "gcc": "4.9.4"
        }

    @property
    def _sources_key(self):
        if self.settings.compiler == "Visual Studio":
            return "Visual Studio"
        elif self.settings.os == "Windows" and self.settings.compiler == "gcc":
            return "mingw"
        return {
            "Android": "Linux",
        }.get(str(self.settings.os), str(self.settings.os))

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        del self.settings.compiler.runtime

    def validate(self):
        compiler = self.settings.compiler
        min_version = self._minimum_compilers_version[str(compiler)]
        try:
            if tools.Version(compiler.version) < min_version:
                msg = (
                    "{} requires C{} features which are not supported by compiler {} {} !!"
                ).format(self.name, self._minimum_cpp_standard, compiler, compiler.version)
                raise ConanInvalidConfiguration(msg)
        except KeyError:
            msg = (
                "{} recipe lacks information about the {} compiler, "
                "support for the required C{} features is assumed"
            ).format(self.name, compiler, self._minimum_cpp_standard)
            self.output.warn(msg)

        try:
            self.conan_data["sources"][self.version][self._sources_key]
        except KeyError:
            raise ConanInvalidConfiguration("Binaries for this combination of architecture/version/os not available")

        if (self.settings.compiler, self.settings.os) == ("gcc", "Windows") and self.options.shared:
            # https://github.com/bytecodealliance/wasmtime/issues/3168
            raise ConanInvalidConfiguration("Shared mingw is currently not possible")

    def build(self):
        tools.get(**self.conan_data["sources"][self.version][self._sources_key][str(self.settings.arch)],
                  destination=self._source_subfolder, strip_root=True)

    def package(self):
        self.copy('LICENSE', src=self._source_subfolder, dst='licenses')
        shutil.copytree(os.path.join(self._source_subfolder, "include"),
                        os.path.join(self.package_folder, "include"))

        srclibdir = os.path.join(self._source_subfolder, "lib")
        if self.options.shared:
            self.copy('wasmtime.dll.lib', src=srclibdir, dst='lib', keep_path=False)
            self.copy('wasmtime.dll', src=srclibdir, dst='bin', keep_path=False)
            self.copy('libwasmtime.dll.a', src=srclibdir, dst='lib', keep_path=False)
            self.copy('libwasmtime.so*', src=srclibdir, dst='lib', keep_path=False)
            self.copy('libwasmtime.dylib', src=srclibdir,  dst='lib', keep_path=False)
        else:
            self.copy('wasmtime.lib', src=srclibdir, dst='lib', keep_path=False)
            self.copy('libwasmtime.a', src=srclibdir, dst='lib', keep_path=False)

    def package_info(self):
        if self.settings.os == "Windows":
            static_suffix = ".lib" if self.settings.compiler == "Visual Studio" else ".a"
            if self.options.shared:
                libsuffix = ".dll{}".format(static_suffix)
            else:
                libsuffix = static_suffix
                self.cpp_info.defines = ["WASM_API_EXTERN=", "WASI_API_EXTERN="]
        else:
            libsuffix = ""
        self.cpp_info.libs = ["wasmtime" + libsuffix]

        if not self.options.shared:
            if self.settings.os == 'Linux':
                self.cpp_info.system_libs = ['pthread', 'dl', 'm']
            elif self.settings.os == "Windows":
                self.cpp_info.system_libs = ['ws2_32', 'bcrypt', 'advapi32', 'userenv', 'ntdll', 'shell32', 'ole32']
