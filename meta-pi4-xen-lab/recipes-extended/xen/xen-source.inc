# Use the official HTTPS mirror for the exact release selected by this layer.
SRC_URI:remove = "git://xenbits.xen.org/xen.git;branch=${XEN_BRANCH}"
SRC_URI:append = " git://github.com/xen-project/xen.git;protocol=https;branch=stable-4.19"
SRCREV = "026c9fa29716b0ff0f8b7c687908e71ba29cf239"
