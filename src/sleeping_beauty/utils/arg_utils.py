def was_explicit(args, field: str) -> bool:
    return hasattr(args, "_explicit_args") and field in args._explicit_args
