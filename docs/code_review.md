# Code review checklist

- Does the change break the pipeline?
- Does it break the Streamlit UI?
- Does it break tests or reduce coverage?
- Does it mix business logic into Streamlit views?
- Does it introduce undocumented data or assumptions?
- Does it contradict assumptions.md?
- Does it change economics, routing, or location without being called out?
- Does it require new tests?
- Does it preserve backward compatibility?

Use /review or a manual review before merging.
