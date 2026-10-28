# The W3C corpus is installed only by do_install_ptest. Keep it when ptest is
# requested, but do not fetch unused test data for this non-ptest lab image.
SRC_URI:remove = "${@'' if d.getVar('PTEST_ENABLED') == '1' else 'http://www.w3.org/XML/Test/xmlts20130923.tar;subdir=libxml2-${PV};name=testtar'}"

# The base recipe runs find on this directory during configure, including
# builds which do not request the test corpus.
python do_patch:append() {
    bb.utils.mkdirhier(d.getVar("S") + "/xmlconf")
}
