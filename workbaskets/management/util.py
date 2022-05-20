class WorkBasketCommandMixin:
    def output_workbasket(self, workbasket, indent=4):
        spaces = " " * indent
        self.stdout.write(f"{spaces}pk: {workbasket.pk}")
        self.stdout.write(f"{spaces}title: {workbasket.title}")
        self.stdout.write(f"{spaces}reason: {workbasket.reason}")
        self.stdout.write(f"{spaces}status: {workbasket.status}")
