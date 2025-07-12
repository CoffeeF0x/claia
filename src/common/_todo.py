# TODO:
# - Refactor to use pluggy for file types?
# - BASEFILE:
#   - Add a validate function to the that verifies that everything is as
#     expected (correct subfolder, mime type, reference, exists, etc)
#   - Add subfolder validation? (loop through each item in subfolder and validate)
#   - Make the base file more cohesive with our state emuns (Local, External/Reference, Empty, etc)
#   - Finish adding streaming support to our save method
#   - Add a method to delete the file (marks as deleted in manifest, with a force delete option?)
# - PROMPT:
#   - Double check the save method. If content is passed, is the metadata inconsistent?
#   - Move save override stuff to post save hook
# - IMAGE:
#   - Overhaul the resize method
#   - Make format function more robust and the output consistent
#   - Make all format metadata setting use the format method
#   - Is format metadata even needed since we have mime type?
#   - Make mime type rely on our enum
# - CONVERSATION:
#   - Attach a file should just send the path or url along with whether or not
#     it's a reference (optional), then identify and call the correct object
#     to attach the file. If a file id is passed, then validate and identify the type
#   - Consider redesign so that an external file load is not required (ie, stored fully
#     in memory except on saves and loads)
#   - Update the function definition to match our commands structure
#   - Remove the settings object from tool calls?
#   - Make sure tools still work after load (ie, are the references stored correctly?)
# - MANIFEST:
#   - 'FileManifest" object has no attribute 'add_file' (from demo)
