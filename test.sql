SELECT "trackedmodel"."id",
       "trackedmodel"."polymorphic_ctype_id",
       "trackedmodel"."workbasket_id",
       ...
       "commodity"."trackedmodel_ptr_id",
       ...
  FROM "commodity"
 INNER JOIN "trackedmodel"
    ON "commodity"."trackedmodel_ptr_id" = "trackedmodel"."id";

SELECT "trackedmodel"."id",
       "trackedmodel"."polymorphic_ctype_id",
       "trackedmodel"."workbasket_id",
       ...
  FROM "trackedmodel"
 WHERE "trackedmodel"."workbasket_id" = 1;

SELECT "trackedmodel"."id",
       "trackedmodel"."polymorphic_ctype_id",
       "trackedmodel"."workbasket_id",
       ...
       "commodity"."trackedmodel_ptr_id",
       ...
  FROM "commodity"
 INNER JOIN "trackedmodel"
    ON "commodity"."trackedmodel_ptr_id" = "trackedmodel"."id"
 WHERE "commodity"."trackedmodel_ptr_id" IN ( 1, 3 );

SELECT "trackedmodel"."id", 
       "trackedmodel"."polymorphic_ctype_id", 
       "trackedmodel"."workbasket_id", 
       ...
       "footnotetype"."trackedmodel_ptr_id", 
       ...
  FROM "footnotetype" 
 INNER JOIN "trackedmodel" 
    ON "footnotetype"."trackedmodel_ptr_id" = "trackedmodel"."id" 
 WHERE "footnotetype"."trackedmodel_ptr_id" IN ( 2 );