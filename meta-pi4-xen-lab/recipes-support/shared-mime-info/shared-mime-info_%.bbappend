# Upstream treats xmlto as optional and uses it only for the HTML specification.
# Keep the MIME tools/data while omitting that documentation-only dependency.
DEPENDS:remove = "xmlto-native"
